from aws_cdk import (
    CfnOutput,
    Stack,
    aws_rds as rds,
    aws_ec2 as ec2,
    Duration,
    RemovalPolicy,
    Fn
)
from constructs import Construct


class DatabaseStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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

        # RDS 인스턴스 생성
        self.rds_instance = rds.DatabaseInstance(
            self,
            "CspcInfraRds",
            database_name="mydatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_8
            ),
            vpc=vpc,  # VPC에 배치
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO  # 프리티어 인스턴스
            ),
            security_groups=[rds_security_group],
            vpc_subnets={
                "subnet_type": ec2.SubnetType.PUBLIC,  # 퍼블릭 서브넷에 배치
            },
            publicly_accessible=True,  # 외부에서 접근 가능
            credentials=rds.Credentials.from_generated_secret("cspclab"),  # 관리자 계정 생성
            allocated_storage=20,  # 최소 스토리지 크기 (프리티어 내)
            backup_retention=Duration.days(1),  # 백업 보존 기간 설정 (1일)
            deletion_protection=False,  # 스택 삭제 시 삭제 허용
            removal_policy=RemovalPolicy.DESTROY,  # 스택 삭제 시 리소스 제거
        )

        # 출력 설정
        CfnOutput(
            self,
            "RdsEndpoint",
            value=self.rds_instance.db_instance_endpoint_address,
            export_name="RdsEndpoint",
        )
