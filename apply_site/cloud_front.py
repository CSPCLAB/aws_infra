from aws_cdk import Stack, aws_s3 as s3, aws_s3_deployment as s3deploy, aws_cloudfront as cloudfront, aws_certificatemanager as acm, aws_route53 as route53, aws_route53_targets as targets
from constructs import Construct
import aws_cdk as cdk


class StaticWebsiteStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, domain_name: str = "apply.cspc.me", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 버킷 생성 (정적 웹사이트 호스팅)
        self.bucket = s3.Bucket(
            self,
            "StaticWebsiteBucket",
            website_index_document="index.html",  # 정적 웹사이트의 기본 파일
            website_error_document="error.html",  # 에러 파일
            public_read_access=True,  # 퍼블릭 읽기 권한 부여
            removal_policy=cdk.RemovalPolicy.DESTROY,  # 스택 삭제 시 S3 버킷 삭제
            auto_delete_objects=True,  # 스택 삭제 시 객체 자동 삭제
        )

        # Route 53에서 Hosted Zone 참조
        self.hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=domain_name,  # GoDaddy 도메인 이름
        )

        # ACM 인증서 생성 (DNS 검증)
        self.certificate = acm.Certificate(
            self,
            "WebsiteCertificate",
            domain_name=f"www.{domain_name}",  # www 서브도메인용 인증서
            validation=acm.CertificateValidation.from_dns(self.hosted_zone),
        )

        # CloudFront 배포 생성 (Custom Domain 연결)
        self.cloudfront_distribution = cloudfront.CloudFrontWebDistribution(
            self,
            "StaticWebsiteCloudFront",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=self.bucket
                    ),
                    behaviors=[cloudfront.Behavior(is_default_behavior=True)],
                )
            ],
            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                self.certificate,
                aliases=[f"www.{domain_name}"],  # CloudFront와 도메인 연결
            ),
        )

        # Route 53 A 레코드 생성 (Alias로 CloudFront 연결)
        route53.ARecord(
            self,
            "WebsiteAliasRecord",
            zone=self.hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.cloudfront_distribution)
            ),
            record_name=f"www.{domain_name}",  # www 서브도메인 설정
        )

        # S3에 정적 파일 업로드
        s3deploy.BucketDeployment(
            self,
            "DeployStaticFiles",
            sources=[s3deploy.Source.asset("./website")],  # 정적 파일 경로 (로컬)
            destination_bucket=self.bucket,
        )

        # 출력
        cdk.CfnOutput(self, "CloudFrontUrl", value=f"https://{self.cloudfront_distribution.distribution_domain_name}")
        cdk.CfnOutput(self, "S3BucketName", value=self.bucket.bucket_name)
        cdk.CfnOutput(self, "CustomDomain", value=f"https://www.{domain_name}")
        print(f"CloudFront URL: https://{self.cloudfront_distribution.distribution_domain_name}")
        print(f"S3 Bucket Name: {self.bucket.bucket_name}")
        print(f"Custom Domain URL: https://www.{domain_name}")
