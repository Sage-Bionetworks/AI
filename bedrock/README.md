# Exploration of AWS bedrock

This is to document the exploration of AWS bedrock and the resources created

## SCCE

### Knowledge Base

1. Log into SCCE dev aws account
1. Create knowledge base (nftc-kb) with a service role
1. See a scratch template in `main.tf` that is untested currently

### Agent
1. Create an agent
1. create a service role for the agent
1. After creation, link it to the knowledge base
1. prepare the agent

## Synapse KB

The creation of the NF knowledge base motivated me to try and create knowledgebases for Synapse.  I extracted all the public project wikis and created uploaded all the markdown files into an S3 bucket.  From there, I created a knowledge base and agent.

