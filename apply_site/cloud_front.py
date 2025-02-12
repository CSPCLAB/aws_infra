from aws_cdk import (
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct


class StaticWebsiteStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, domain_name: str = "apply.cspc.me", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        AlbEndpoint = Fn.import_value("ALBEndpoint")

        # S3 버킷 생성 (정적 웹사이트 호스팅)
        self.bucket = s3.Bucket(
            self,
            "StaticWebsiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            website_index_document="index.html",
            website_error_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
        )

        # S3 버킷 정책 추가 (CloudFront 접근 허용)
        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[self.bucket.arn_for_objects("*")],
                principals=[iam.AnyPrincipal()],
            )
        )

        # ACM에서 기존 발급된 인증서 가져오기
        self.certificate = acm.Certificate.from_certificate_arn(
            self,
            "WebsiteCertificate",
            certificate_arn="arn:aws:acm:us-east-1:867344471687:certificate/10906980-1c6b-4b1d-aa5e-8b50fca5ab4a"
        )

        # CloudFront 배포 생성 (Custom Domain 연결)
        self.cloudfront_distribution = cloudfront.Distribution(
            self,
            "StaticWebsiteCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3StaticWebsiteOrigin(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            domain_names=[domain_name],
            certificate=self.certificate,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
            additional_behaviors={
                "/api*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(AlbEndpoint,protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
                ),
                "/admin*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(AlbEndpoint,protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
                ),
            },
            price_class=cloudfront.PriceClass.PRICE_CLASS_200,
            geo_restriction=cloudfront.GeoRestriction.allowlist("KR"),
        )

        # CDK 출력값
        CfnOutput(self, "CloudFrontUrl", value=f"https://{self.cloudfront_distribution.distribution_domain_name}")
        CfnOutput(self, "S3BucketName", value=self.bucket.bucket_name)
        print(f"CloudFront URL: https://{self.cloudfront_distribution.distribution_domain_name}")
        print(f"S3 Bucket Name: {self.bucket.bucket_name}")
