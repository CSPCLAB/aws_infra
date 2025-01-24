import aws_cdk as core
import aws_cdk.assertions as assertions

from cspc_infra.cspc_infra_stack import CspcInfraStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cspc_infra/cspc_infra_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CspcInfraStack(app, "cspc-infra")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
