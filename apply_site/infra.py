from aws_cdk import Stack, aws_ec2 as ec2, CfnOutput
from constructs import Construct


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC 생성
        self.vpc = ec2.Vpc(
            self,
            "CspcInfraVpc",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public-subnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                )
            ],
            nat_gateways=0,  # NAT 게이트웨이 없이 비용 절감
        )

        # RDS용 보안 그룹 생성
        self.rds_security_group = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=self.vpc,
            description="Allow database access",
            allow_all_outbound=True,
        )

        # VPC와 RDS 보안 그룹 정보를 출력
        CfnOutput(self, "VpcId", value=self.vpc.vpc_id, export_name="VpcId")
        CfnOutput(
            self,
            "RdsSecurityGroupId",
            value=self.rds_security_group.security_group_id,
            export_name="RdsSecurityGroupId",
        )

        # 각 서브넷 ID를 출력
        for idx, subnet in enumerate(self.vpc.public_subnets):
            CfnOutput(
                self,
                f"PublicSubnet{idx+1}Id",
                value=subnet.subnet_id,
                export_name=f"PublicSubnet{idx+1}Id",
            )
