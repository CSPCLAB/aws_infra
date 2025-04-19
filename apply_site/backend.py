from aws_cdk import Duration, Stack, aws_ec2 as ec2, aws_iam as iam, aws_s3 as s3, aws_elasticloadbalancingv2 as elbv2, aws_logs as logs, CfnOutput, Fn, aws_elasticloadbalancingv2_targets as targets
from constructs import Construct


class BackendStack(Stack):
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


        # EC2 보안 그룹 생성
        ec2_security_group = ec2.SecurityGroup(
            self,
            "EC2InstanceSecurityGroup",
            vpc=vpc,
            description="Allow traffic to/from EC2",
            allow_all_outbound=True,
        )

        # RDS 보안 그룹에 EC2 접근 허용
        rds_security_group.add_ingress_rule(
            peer=ec2_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow EC2 instance access to RDS",
        )

        # IAM 역할 생성 (EC2 인스턴스용)
        ec2_role = iam.Role(
            self,
            "Ec2InstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )

        # EC2 인스턴스 생성
        ec2_instance = ec2.Instance(
            self,
            "BackendInstance",
            instance_type=ec2.InstanceType("t4g.small"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(cpu_type=ec2.AmazonLinuxCpuType.ARM_64),
            vpc=vpc,
            security_group=ec2_security_group,
            role=ec2_role,
            user_data=ec2.UserData.custom(
                """
                #!/bin/bash
                yum install -y docker
                systemctl enable --now docker
                """
            ),
        )

        # ALB 보안 그룹 생성
        alb_security_group = ec2.SecurityGroup(
            self,
            "ALBSecurityGroup",
            vpc=vpc,
            description="Allow HTTP traffic to ALB",
            allow_all_outbound=True,
        )
        alb_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP")

        # ALB 생성
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "BackendALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
        )

        # Target Group 생성 (EC2를 대상으로 지정)
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "BackendTargetGroup",
            vpc=vpc,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=80,
            targets=[targets.InstanceTarget(ec2_instance)],
            health_check=elbv2.HealthCheck(
                path="/",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )

        # ALB 리스너 생성 (HTTP)
        listener = alb.add_listener(
            "Listener",
            port=80,
            open=True,
            default_action=elbv2.ListenerAction.forward([target_group]),
        )

        # ALB 리스너 규칙 생성 (HTTP -> Target Group)
        ec2_security_group.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from ALB"
        )

        # ALB의 DNS 출력
        CfnOutput(self, "ALBEndpoint", value=alb.load_balancer_dns_name,export_name="ALBEndpoint")
