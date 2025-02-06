from aws_cdk import Stack, aws_s3 as s3, aws_s3_deployment as s3deploy, aws_cloudfront as cloudfront, aws_certificatemanager as acm, aws_route53 as route53, aws_route53_targets as targets, aws_cloudfront_origins as origins, aws_iam as iam
from constructs import Construct
import aws_cdk as cdk


class StaticWebsiteStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, domain_name: str = "apply.cspc.me", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 버킷 생성 (정적 웹사이트 호스팅)
        self.bucket = s3.Bucket(
            self,
            "StaticWebsiteBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            website_index_document="index.html",
            website_error_document="index.html",  # 오류 시 index.html 반환
            public_read_access=True, 
            block_public_access=s3.BlockPublicAccess(  # 퍼블릭 액세스 제한을 최소화
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
        )

        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[self.bucket.arn_for_objects("*")],
                principals=[iam.AnyPrincipal()],
            )
        )
        

        # Route 53에서 Hosted Zone 참조
        # self.hosted_zone = route53.HostedZone.from_lookup(
        #     self,
        #     "HostedZone",
        #     domain_name=domain_name,  # GoDaddy 도메인 이름
        # )

        # ACM 인증서 생성 (DNS 검증)
        # self.certificate = acm.Certificate(
        #     self,
        #     "WebsiteCertificate",
        #     domain_name=f"www.{domain_name}",  # www 서브도메인용 인증서
        #     validation=acm.CertificateValidation.from_dns(self.hosted_zone),
        # )

        # CloudFront 배포 생성 (Custom Domain 연결)
        self.cloudfront_distribution = cloudfront.Distribution(
            self,
            "StaticWebsiteCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3StaticWebsiteOrigin(self.bucket),  # S3 정적 웹사이트 엔드포인트 사용
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            error_responses=[  # CSR 문제 해결을 위한 설정 (404 에러 시 index.html 반환)
                cloudfront.ErrorResponse(
                    http_status=403,  # S3에서 파일이 없을 때 403 반환
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),  # 즉시 적용
                ),
                cloudfront.ErrorResponse(
                    http_status=404,  # 없는 페이지 접근 시 index.html 반환
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_200,
            geo_restriction=cloudfront.GeoRestriction.allowlist("KR"),  # 한국에서만 접근 가능
        )

        # Route 53 A 레코드 생성 (Alias로 CloudFront 연결)
        # route53.ARecord(
        #     self,
        #     "WebsiteAliasRecord",
        #     zone=self.hosted_zone,
        #     target=route53.RecordTarget.from_alias(
        #         targets.CloudFrontTarget(self.cloudfront_distribution)
        #     ),
        #     record_name=f"www.{domain_name}",  # www 서브도메인 설정
        # )

        # S3에 정적 파일 업로드
        # s3deploy.BucketDeployment(
        #     self,
        #     "DeployStaticFiles",
        #     sources=[s3deploy.Source.asset("./website")],  # 정적 파일 경로 (로컬)
        #     destination_bucket=self.bucket,
        # )

        # 출력
        cdk.CfnOutput(self, "CloudFrontUrl", value=f"https://{self.cloudfront_distribution.distribution_domain_name}")
        cdk.CfnOutput(self, "S3BucketName", value=self.bucket.bucket_name)
        print(f"CloudFront URL: https://{self.cloudfront_distribution.distribution_domain_name}")
        print(f"S3 Bucket Name: {self.bucket.bucket_name}")
