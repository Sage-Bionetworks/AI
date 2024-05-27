import json

import aws_cdk as core
from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
    aws_bedrock,
    aws_opensearchserverless,
    Stack,
)
from constructs import Construct


class BedrockInfraStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Get current AWS account details
        # sts_client = sts.CfnCallerIdentity(self, "CallerIdentity")

        # Get current region
        current_region = self.region
        account = self.account

        # Get current partition
        current_partition = core.Aws.PARTITION

        # S3 Bucket
        nftc_kb_bucket = s3.Bucket(
            self,
            "NftcKbBucket",
            bucket_name="tyu-testing-bucket-cdk",
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        # IAM Policy Document for Agent Trust
        agent_trust_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    principals=[iam.ServicePrincipal("bedrock.amazonaws.com")],
                    conditions={
                        "StringEquals": {"aws:SourceAccount": account},
                        "ArnLike": {
                            "AWS:SourceArn": f"arn:{current_partition}:bedrock:{current_region}:{account}:agent/*"
                        },
                    },
                )
            ]
        )

        # IAM Policy Document for Foundation Model
        foundation_model_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["bedrock:InvokeModel"],
                    resources=[
                        f"arn:{current_partition}:bedrock:{current_region}::foundation-model/anthropic.claude-v2",
                        f"arn:{current_partition}:bedrock:{current_region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    ],
                )
            ]
        )

        # IAM Policy Document for Retrieve Knowledge Base
        retrieve_kb_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["bedrock:Retrieve"],
                    resources=[
                        f"arn:{current_partition}:bedrock:{current_region}:{account}:knowledge-base/{nftc_kb_bucket.bucket_arn}"
                    ],
                )
            ]
        )

        # IAM Role for Knowledge Base
        nftc_kb_role = iam.Role(
            self,
            "NftcKbRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "NftcKbPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket", "s3:GetObject", "s3:PutObject"],
                            resources=[
                                nftc_kb_bucket.bucket_arn,
                                f"{nftc_kb_bucket.bucket_arn}/*",
                            ],
                        )
                    ]
                )
            },
            role_name="nftc-kb-role",
        )
        opensearch_encryption_config = aws_opensearchserverless.CfnSecurityPolicy(
            self,
            "NftcOpenSearchEncryptionPolicy",
            name="nftcopensearchencryptionpolicy",
            type="encryption",
            policy=json.dumps({
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/nftc-collection"]}
                ],
                "AWSOwnedKey": True,
            }),
        )
        opensearch_network_config = aws_opensearchserverless.CfnSecurityPolicy(
            self,
            "NftcOpenSearchNetworkPolicy",
            name="nftcopensearchnetworkpolicy",
            type="network",
            # TODO: parametrize collection name
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "Resource": [f"collection/nftc-collection"],
                            "ResourceType": "dashboard",
                        },
                        {
                            "Resource": [f"collection/nftc-collection"],
                            "ResourceType": "collection",
                        },
                    ],
                    "AllowFromPublic": True,
                }
            ]),
        )
        nftc_collection = aws_opensearchserverless.CfnCollection(
            self,
            "NftcCollection",
            name="nftc-collection",
            type="VECTORSEARCH",
            # the properties below are optional
            # description="description",
            # standby_replicas="standbyReplicas",
            # tags={"name": "value"}
        )
        nftc_collection.add_dependency(opensearch_encryption_config)
        nftc_collection.add_dependency(opensearch_network_config)
        # Description: OpenSearch Serverless encryption policy template
        # Resources:
        # TestSecurityPolicy:
        #     Type: 'AWS::OpenSearchServerless::SecurityPolicy'
        #     Properties:
        #     Name: logs-encryption-policy
        #     Type: encryption
        #     Description: Encryption policy for test collections
        #     Policy: >-
        #         {"Rules":[{"ResourceType":"collection","Resource":["collection/logs*"]}],"AWSOwnedKey":true}
        # Bedrock Knowledge Base
        nftc_kb = aws_bedrock.CfnKnowledgeBase(
            self,
            "NftcKb",
            name="nftc-kb",
            role_arn=nftc_kb_role.role_arn,
            knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
                ),
            ),
            storage_configuration=aws_bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=aws_bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=nftc_collection.attr_arn,
                    field_mapping=aws_bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        metadata_field="nftc-metadata",
                        text_field="nftc-text",
                        vector_field="nftc-vector",
                    ),
                    vector_index_name="nftc-vector",
                ),
            ),
            # tags={
            #     "Name": "nftc-kb"
            # }
        )

        # Bedrock Data Source
        aws_bedrock.CfnDataSource(
            self,
            "NftcKbDataSource",
            knowledge_base_id=nftc_kb.attr_knowledge_base_id,
            name="nftc-kb-datasource",
            data_deletion_policy="DELETE",
            data_source_configuration=aws_bedrock.CfnDataSource.DataSourceConfigurationProperty(
                s3_configuration=aws_bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=nftc_kb_bucket.bucket_arn,
                ),
                type="S3",
            ),
        )

        # IAM Role for Agent
        nftc_agent_role = iam.Role(
            self,
            "NftcAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "FoundationModelPolicy": foundation_model_policy_document,
                "RagPolicy": retrieve_kb_policy_document,
            },
            role_name="nftc-agent-role",
        )

        # Bedrock Agent
        aws_bedrock.CfnAgent(
            self,
            "NftcAgent",
            agent_name="nftc-agent",
            agent_resource_role_arn=nftc_agent_role.role_arn,
            foundation_model="anthropic.claude-v3-sonnet",
            instruction="""
            Your task is to extract data about research tools, such as animal models and cell lines biobanks from scientific publications. When provided with a name or synonym for a research tool, you will generate a comprehensive list of temporal "observations" about the research tool that describe the natural history of the model as they relate to development or age. For example, an observation could be "The pigs developed tumor type X at Y months of age." Do not include observations about humans with NF1.
            """,
            knowledge_bases=[
                aws_bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                    description="description",
                    knowledge_base_id=nftc_kb.attr_knowledge_base_id,
                    # the properties below are optional
                    # knowledge_base_state="knowledgeBaseState"
                )
            ],
            prompt_override_configuration=aws_bedrock.CfnAgent.PromptOverrideConfigurationProperty(
                prompt_configurations=[
                    aws_bedrock.CfnAgent.PromptConfigurationProperty(
                        base_prompt_template="""
                        You are a data extraction agent. I will provide you with a set of search results. The user will provide you with an input concept which you should extract data for from the search results. Your job is to answer the user's question using only information from the search results. If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion.
                        Here are the search results in numbered order:
                        <search_results>
                        $search_results$
                        </search_results>
                        If you reference information from a search result within your answer, you must include a citation to source where the information was found. Each result has a corresponding source ID that you should reference.
                        Do NOT directly quote the <search_results> in your answer. Your job is to answer the user's question as concisely as possible.
                        You must output your answer in the following format. Pay attention and follow the formatting and spacing exactly:
                        <answer>
                        <answer_part>
                        <text>
                        [
                        {
                            "resourceName": "the resource name, likely the same as the input concept from the user",
                            "resourceType": ["Animal Model", "Cell Line"],
                            "observationText": "This is an example sentence.",
                            "observationType": [
                                "Body Length",
                                "Body weight",
                                "Coat Color",
                                "Disease Susceptibility",
                                "Feed Intake",
                                "Feeding Behavior",
                                "Growth rate",
                                "Motor Activity",
                                "Organ Development",
                                "Reflex Development",
                                "Reproductive Behavior",
                                "Social Behavior",
                                "Swimming Behavior",
                                "Tumor Growth",
                                "Issue",
                                "Depositor Comment",
                                "Usage Instructions",
                                "General Comment or Review",
                                "Other"
                            ],
                            "observationPhase": ["prenatal", "postnatal", null],
                            "observationTime": "a double; the time during the development of the organism at which the observation occurred",
                            "observationTimeUnits": ["days", "weeks", "months", "years"],
                            "sourcePublication": "pubmed ID or DOI"
                        },
                        ]
                        </text>
                        <sources>
                        <source>source ID</source>
                        </sources>
                        </answer_part>
                        </answer_part>
                        </answer>
                        """,
                        inference_configuration=aws_bedrock.CfnAgent.InferenceConfigurationProperty(
                            maximum_length=2048,
                            stop_sequences=["Human"],
                            temperature=0,
                            top_k=250,
                            top_p=1,
                        ),
                        parser_mode="DEFAULT",
                        prompt_creation_mode="OVERRIDDEN",
                        prompt_state="ENABLED",
                        prompt_type="KNOWLEDGE_BASE_RESPONSE_GENERATION",
                    )
                ],
                override_lambda=None,
                # tags=[core.CfnTag(
                #     key="Name",
                #     value="nftc-agent"
                # )]
            ),
        )

        # Bedrock Agent Knowledge Base Association
        # aws_bedrock.CfnAgentKnowledgeBaseAssociation(self, "NftcKbAssociation",
        #     agent_id=nftc_agent_role.role_arn,
        #     knowledge_base_id=nftc_kb.ref,
        #     knowledge_base_state="ENABLED",
        #     description="Example Knowledge base"
        # )
