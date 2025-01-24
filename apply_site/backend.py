from aws_cdk import Stack, aws_ec2 as ec2, aws_iam as iam, Fn
from constructs import Construct


class Ec2BackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC 가져오기
        vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "ImportedVpc",
            vpc_id=Fn.import_value("VpcId"),
            availability_zones=["ap-northeast-2a", "ap-northeast-2b"],
            public_subnet_ids=[
                Fn.import_value("PublicSubnet1Id"),
                Fn.import_value("PublicSubnet2Id"),
            ],
        )

        # 보안 그룹 가져오기
        rds_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "ImportedRdsSecurityGroup", security_group_id=Fn.import_value("RdsSecurityGroupId")
        )

        # RDS 엔드포인트 가져오기
        rds_endpoint = Fn.import_value("RdsEndpoint")

        # EC2 보안 그룹 생성
        ec2_security_group = ec2.SecurityGroup(
            self,
            "Ec2BackendSecurityGroup",
            vpc=vpc,
            description="Allow traffic to/from EC2 for backend",
            allow_all_outbound=True,
        )

        # RDS 보안 그룹에 EC2 접근 허용
        rds_security_group.add_ingress_rule(
            peer=ec2_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow EC2 backend access to RDS",
        )

        # IAM 역할 생성
        ec2_role = iam.Role(
            self,
            "Ec2BackendRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )

        # EC2 인스턴스 생성
        ec2_instance = ec2.Instance(
            self,
            "BackendInstance",
            instance_type=ec2.InstanceType("t4g.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(cpu_type=ec2.AmazonLinuxCpuType.ARM_64),
            vpc=vpc,
            role=ec2_role,
            security_group=ec2_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        # User Data 스크립트 (Docker 컨테이너 실행)
        ec2_instance.add_user_data(
            "#!/bin/bash",
            "yum update -y",
            f"echo 'export DB_ENDPOINT={rds_endpoint}' >> /etc/environment",
        )
