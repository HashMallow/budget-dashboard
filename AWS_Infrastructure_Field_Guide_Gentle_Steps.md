# AWS Infrastructure Field Guide for Software Engineers

**Gentle step-by-step edition: Console + CLI + Terraform later**

Prepared for: Alireza Mahmoudi  
Focus: Surface-level understanding of AWS parts, without a baptism of fire.

> This is not a build-everything roadmap. It is a field guide. Learn what each part does, inspect it in the console, inspect it with CLI, then use the two projects only as examples.

## How to Use This Guide

- **Console first** when a service is new and visual.
- **CLI second** to inspect real AWS API objects.
- **Terraform later** only after you can explain the resource.
- **Projects are examples**, not the main structure.

## Gentle Learning Ladder

### Step 0: Set guardrails first
- **Do:** Create AWS Budget, choose one region, configure CLI or CloudShell, run sts get-caller-identity.
- **Done when:** No app work yet. This prevents accidental fire.

### Step 1: Read the network map
- **Do:** VPC, subnets, route tables, security groups, IGW. Inspect only; do not build a custom VPC yet.
- **Done when:** You can explain why a subnet is public.

### Step 2: Run one server
- **Do:** EC2 in a public subnet, simple FastAPI health endpoint, systemd or Docker, one security group.
- **Done when:** You can SSH/SSM in, check logs, and stop/terminate cleanly.

### Step 3: Add object storage
- **Do:** S3 bucket for one tiny XLSX upload. Learn object key, bucket policy, and cleanup.
- **Done when:** You know the difference between file storage and relational rows.

### Step 4: Move database carefully
- **Do:** RDS PostgreSQL after local Postgres works. Keep RDS private.
- **Done when:** You can explain app SG -> RDS SG access.

### Step 5: Observe before scaling
- **Do:** CloudWatch logs, log retention, one alarm, Cost Explorer review.
- **Done when:** You can debug without guessing or only SSHing.

### Step 6: Add stable entry point
- **Do:** ALB only after one EC2 app works. Learn listener -> target group -> target health.
- **Done when:** You understand health checks.

### Step 7: Automate known steps
- **Do:** GitHub Actions tests first, then OIDC deploy. Terraform only after console/CLI familiarity.
- **Done when:** Automation is now repetition, not magic.

### Step 8: Container platform later
- **Do:** ECR -> ECS -> Fargate once EC2, ALB, IAM, logs, and security groups are comfortable.
- **Done when:** You know what ECS is hiding from you.

### Step 9: Async and cache only when needed
- **Do:** SQS + Go worker for slow imports; Valkey only for measured cache/rate-limit/session/job-status need.
- **Done when:** You solve real bottlenecks, not imaginary architecture problems.

### Step 10: Advanced extensions
- **Do:** EKS, QuickSight, Athena, Glue only after the base system is clear.
- **Done when:** No baptism of fire.

## Service Cards

## Networking

### VPC - Virtual Private Cloud

**What it does:** Your isolated AWS network boundary. EC2, RDS, ALB, ECS tasks, subnets, route tables, security groups, and endpoints are organized inside it.

**Console path:** VPC -> Your VPCs -> CIDR block, default VPC status, route tables, subnets.

**CLI:**
```bash
aws ec2 describe-vpcs --query "Vpcs[*].{VpcId:VpcId,Cidr:CidrBlock,Default:IsDefault}" --output table
```

**First tiny step:** Open the VPC console and identify the default VPC. Then run the CLI command and match the VPC ID.

**Beginner trap:** The VPC itself is not usually the cost problem. Cost hides in NAT Gateways, endpoints, load balancers, data transfer, and always-on services inside the VPC.

**Project context:** Both projects eventually live inside a VPC. For the first FastAPI deploy, you only need to understand one VPC and one public subnet.

**Official docs:** https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html

### Public and Private Subnets - AZ-scoped network slices

**What it does:** A subnet is a slice of your VPC CIDR in one Availability Zone. A public subnet has a route to an Internet Gateway; a private subnet does not accept direct inbound internet traffic.

**Console path:** VPC -> Subnets -> Route table association and Availability Zone.

**CLI:**
```bash
aws ec2 describe-subnets --query "Subnets[*].{Id:SubnetId,Cidr:CidrBlock,Az:AvailabilityZone,MapPublicIp:MapPublicIpOnLaunch}" --output table
```

**First tiny step:** Pick one subnet and inspect its route table. The route table decides public vs private, not the name alone.

**Beginner trap:** Calling a subnet public just because an instance has a public IP. The route table is the source of truth.

**Project context:** Use a public subnet for the first EC2 learning deployment. Put RDS in private subnets later.

**Official docs:** https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html

### Route Tables - Where packets go

**What it does:** Route tables decide whether subnet traffic stays local, goes to the internet, goes through NAT, or reaches another network path.

**Console path:** VPC -> Route Tables -> Routes and subnet associations.

**CLI:**
```bash
aws ec2 describe-route-tables --query "RouteTables[*].{Id:RouteTableId,Routes:Routes[*].DestinationCidrBlock}" --output table
```

**First tiny step:** Find the route table associated with your EC2 subnet. Look for 0.0.0.0/0 and its target.

**Beginner trap:** Debugging only security groups. If the route is missing, a perfect security group will not fix connectivity.

**Project context:** When FastAPI cannot reach the internet or RDS, routes are one of the first things to inspect.

**Official docs:** https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html

### Internet Gateway - Public internet exit/entry

**What it does:** An Internet Gateway lets resources in public subnets communicate with the internet when the route table points to it.

**Console path:** VPC -> Internet Gateways -> Attachment status.

**CLI:**
```bash
aws ec2 describe-internet-gateways --output table
```

**First tiny step:** Open your public subnet route table and confirm the 0.0.0.0/0 route points to an igw-* target.

**Beginner trap:** Attaching an Internet Gateway is not enough; the subnet route table must route to it.

**Project context:** A public EC2 instance and public-facing ALB require an Internet Gateway path.

**Official docs:** https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html

### Security Groups - Stateful firewalls

**What it does:** Security groups are stateful firewall rules attached to resources like EC2, ALB, RDS, and ECS tasks.

**Console path:** EC2 or VPC -> Security Groups -> Inbound rules and outbound rules.

**CLI:**
```bash
aws ec2 describe-security-groups --query "SecurityGroups[*].{Name:GroupName,Id:GroupId}" --output table
```

**First tiny step:** Inspect one security group and explain every inbound rule in one sentence.

**Beginner trap:** Opening SSH, PostgreSQL, Redis/Valkey, or admin ports to 0.0.0.0/0.

**Project context:** ALB accepts HTTP/HTTPS from the internet. Backend accepts only from ALB SG. RDS accepts only from backend SG.

**Official docs:** https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html

### NAT Gateway - Outbound internet for private subnets

**What it does:** NAT Gateway allows resources in private subnets to reach the internet without being directly reachable from the internet.

**Console path:** VPC -> NAT Gateways -> Subnet, Elastic IP, state.

**CLI:**
```bash
aws ec2 describe-nat-gateways --query "NatGateways[*].{Id:NatGatewayId,State:State,Subnet:SubnetId}" --output table
```

**First tiny step:** Do not create one yet. Just learn what route table entry would use it: 0.0.0.0/0 -> nat-*.

**Beginner trap:** Always-on NAT Gateway is a common early cost surprise. Avoid it until private workloads truly need outbound internet.

**Project context:** Later ECS tasks in private subnets may use NAT unless you replace some paths with VPC endpoints.

**Official docs:** https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html

### VPC Endpoints - Private paths to AWS services

**What it does:** Endpoints let resources in your VPC access AWS services like S3, ECR, CloudWatch, and Secrets Manager without public internet routing.

**Console path:** VPC -> Endpoints -> Service name, endpoint type, subnet, security group.

**CLI:**
```bash
aws ec2 describe-vpc-endpoints --query "VpcEndpoints[*].{Id:VpcEndpointId,Service:ServiceName,State:State}" --output table
```

**First tiny step:** Read about S3 Gateway Endpoints before creating interface endpoints. Understand endpoint type differences.

**Beginner trap:** Interface endpoints have their own hourly/data cost. They are useful, but not automatically cheaper than NAT in every case.

**Project context:** Useful later when ECS/Fargate tasks in private subnets need private S3/ECR/CloudWatch access.

**Official docs:** https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html

### ALB - Application Load Balancer

**What it does:** Layer 7 HTTP/HTTPS load balancer. Handles listeners, target groups, health checks, host/path routing, TLS, and WAF integration.

**Console path:** EC2 -> Load Balancers -> Listeners, Target Groups, Health checks.

**CLI:**
```bash
aws elbv2 describe-load-balancers --output table
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN
```

**First tiny step:** Study the shape first: Load Balancer -> Listener -> Rule -> Target Group -> Targets.

**Beginner trap:** An ALB has a standing cost even with very low traffic. Use it when you need stable HTTP routing or multiple targets.

**Project context:** Put FastAPI behind ALB after single EC2 deployment works. Later route app/API domains cleanly.

**Official docs:** https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html

### NLB - Network Load Balancer

**What it does:** Layer 4 load balancer for TCP/UDP/TLS-style traffic, static IP style needs, and very high-performance network flows.

**Console path:** EC2 -> Load Balancers -> Type: Network.

**CLI:**
```bash
aws elbv2 describe-load-balancers --query "LoadBalancers[?Type==`network`]" --output table
```

**First tiny step:** Do not start here. Compare it with ALB: NLB is network-layer; ALB is HTTP-aware.

**Beginner trap:** Using NLB for a normal web dashboard and losing easy HTTP path/header routing features.

**Project context:** Usually not needed for your first FastAPI/dashboard work. Mention it as a comparison item.

**Official docs:** https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html

### Route 53 - DNS

**What it does:** DNS service for hosted zones and records. Maps domain names to ALB, CloudFront, or other endpoints.

**Console path:** Route 53 -> Hosted Zones -> Records.

**CLI:**
```bash
aws route53 list-hosted-zones
```

**First tiny step:** Learn A/AAAA/CNAME/alias records at a surface level before buying or moving domains.

**Beginner trap:** DNS changes can take time. Hosted zones and queries have pricing. Verify current pricing before use.

**Project context:** api.yourdomain.com can point to ALB; dashboard.yourdomain.com can point to CloudFront or ALB.

**Official docs:** https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html

## Compute

### EC2 - Virtual machines

**What it does:** A server you can SSH into. Best first cloud deployment because it exposes Linux, ports, processes, logs, systemd, reverse proxies, and IAM roles.

**Console path:** EC2 -> Instances -> State, public IP, subnet, security group, IAM role, storage.

**CLI:**
```bash
aws ec2 describe-instances --query "Reservations[*].Instances[*].{Id:InstanceId,State:State.Name,Ip:PublicIpAddress}" --output table
```

**First tiny step:** Launch a tiny instance only after setting a budget. SSH/SSM in and run a simple health endpoint.

**Beginner trap:** Leaving instances, EBS volumes, or public IPv4 addresses around after experiments.

**Project context:** First real deployment for FastAPI. Do EC2 before ECS so infrastructure stops feeling magical.

**Official docs:** https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html

### ECR - Container image registry

**What it does:** Stores Docker/container images. It does not run containers; ECS/Fargate/EC2 run them.

**Console path:** ECR -> Repositories -> Images and tags.

**CLI:**
```bash
aws ecr describe-repositories
aws ecr describe-images --repository-name REPO_NAME
```

**First tiny step:** Create a repo only when you are ready to push an image. Practice describe commands first.

**Beginner trap:** Thinking ECR is a compute service. It is storage for images.

**Project context:** Store FastAPI and Go worker images before moving to ECS/Fargate.

**Official docs:** https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html

### ECS - Container orchestration

**What it does:** Runs containers as tasks and services. Simpler than Kubernetes for many AWS-native web apps.

**Console path:** ECS -> Clusters -> Services -> Tasks -> Logs.

**CLI:**
```bash
aws ecs list-clusters
aws ecs describe-services --cluster CLUSTER --services SERVICE
```

**First tiny step:** Do not create it first. Learn EC2, security groups, CloudWatch logs, ECR, and ALB health checks first.

**Beginner trap:** Starting with ECS before understanding IAM task roles, target groups, image tags, networking mode, and log drivers.

**Project context:** Later: FastAPI API service and Go worker service run as separate ECS services.

**Official docs:** https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started.html

### Fargate - Serverless container capacity

**What it does:** Runs ECS containers without you managing EC2 instances. You still define CPU, memory, networking, logs, and IAM.

**Console path:** ECS service or task -> Launch type: Fargate.

**CLI:**
```bash
aws ecs describe-task-definition --task-definition TASK_DEF
aws ecs update-service --cluster CLUSTER --service SERVICE --force-new-deployment
```

**First tiny step:** Use it after the container image, ALB, and CloudWatch flow make sense.

**Beginner trap:** Serverless does not mean free. Running tasks cost money even if traffic is low.

**Project context:** Good replacement for manual EC2 once you want less server management.

**Official docs:** https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html

### Lambda - Event functions

**What it does:** Runs short-lived code in response to events. Good for small glue jobs, not a substitute for every backend.

**Console path:** Lambda -> Functions -> Configuration -> Triggers -> Monitor.

**CLI:**
```bash
aws lambda list-functions
aws lambda invoke --function-name NAME out.json
```

**First tiny step:** Read the timeout and packaging constraints before considering it for file processing.

**Beginner trap:** Forcing a long-running web API or heavy XLSX processing job into Lambda too early.

**Project context:** Optional small helper later. FastAPI remains the main API; Go worker owns imports.

**Official docs:** https://docs.aws.amazon.com/lambda/latest/dg/welcome.html

### EKS - Managed Kubernetes

**What it does:** AWS managed Kubernetes. Powerful, but adds clusters, nodes, pods, services, ingress, IAM integration, Helm, and autoscaling complexity.

**Console path:** EKS -> Clusters -> Workloads.

**CLI:**
```bash
aws eks list-clusters
kubectl get pods -A
kubectl logs POD_NAME
```

**First tiny step:** Defer. Learn ECS/Fargate, IAM, VPCs, ALB, CloudWatch, and CI/CD first.

**Beginner trap:** Creating a cluster as a beginner and leaving it running, then paying for complexity you are not using.

**Project context:** Optional advanced portfolio phase only if Kubernetes is a job target.

**Official docs:** https://www.eksworkshop.com/

## Data & Storage

### S3 - Object storage

**What it does:** Stores files as objects. Great for raw XLSX uploads, exports, static assets, backups, and logs. Not a relational database.

**Console path:** S3 -> Buckets -> Objects -> Permissions -> Lifecycle rules.

**CLI:**
```bash
aws s3 ls
aws s3 cp sample.xlsx s3://BUCKET/imports/sample.xlsx
aws s3api head-object --bucket BUCKET --key imports/sample.xlsx
```

**First tiny step:** Create a throwaway bucket, upload one tiny file, inspect it, then delete it.

**Beginner trap:** Making buckets public or letting experiment files accumulate without lifecycle/cleanup rules.

**Project context:** Raw XLSX files live in S3. Clean normalized rows live in PostgreSQL.

**Official docs:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html

### CloudFront - CDN

**What it does:** Content delivery network. Caches and serves static/frontend content from edge locations and can front S3 or ALB origins.

**Console path:** CloudFront -> Distributions -> Origins -> Behaviors -> Invalidations.

**CLI:**
```bash
aws cloudfront list-distributions
```

**First tiny step:** Do not add CDN until you know what your origin is. Learn S3/ALB first.

**Beginner trap:** Cache invalidation confusion: the old frontend keeps showing because the CDN is doing its job.

**Project context:** Later: React dashboard static assets can be served from S3 + CloudFront.

**Official docs:** https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html

### RDS PostgreSQL - Managed relational database

**What it does:** Managed PostgreSQL: provisioning, backups, patch options, monitoring hooks. You still own schema design, indexes, migrations, and query quality.

**Console path:** RDS -> Databases -> Connectivity, backups, monitoring, logs.

**CLI:**
```bash
aws rds describe-db-instances --query "DBInstances[*].{DB:DBInstanceIdentifier,Status:DBInstanceStatus,Endpoint:Endpoint.Address}" --output table
```

**First tiny step:** Move to RDS only after local PostgreSQL and EC2 app deployment are understandable.

**Beginner trap:** Making RDS public or leaving it always-on during idle experiments. Verify current pricing before use.

**Project context:** Marketing dashboard tables move from local Compose PostgreSQL to private RDS.

**Official docs:** https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html

### Aurora PostgreSQL - AWS cloud-native PostgreSQL-compatible DB

**What it does:** Aurora is PostgreSQL-compatible but has different storage, high availability, and scaling characteristics than standard RDS PostgreSQL.

**Console path:** RDS -> Databases -> Aurora clusters.

**CLI:**
```bash
aws rds describe-db-clusters --output table
```

**First tiny step:** Read the difference; do not use it as the first managed database.

**Beginner trap:** Choosing Aurora because it sounds advanced before standard RDS is insufficient.

**Project context:** Optional comparison later. Standard RDS PostgreSQL is enough for the MVP.

**Official docs:** https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html

### ElastiCache for Valkey - Managed in-memory cache

**What it does:** Managed Redis-compatible/Valkey cache for low-latency temporary state: caching, rate limits, sessions, locks, and job progress.

**Console path:** ElastiCache -> Valkey caches -> endpoints, subnet groups, security groups.

**CLI:**
```bash
aws elasticache describe-serverless-caches
aws elasticache describe-cache-clusters
```

**First tiny step:** Run local Valkey in Docker first: docker run --rm -p 6379:6379 valkey/valkey:latest

**Beginner trap:** Adding cache before the database model and SQL queries are correct. Cache adds invalidation problems.

**Project context:** Add only for measured dashboard query latency, API rate limits, session state, or temporary import progress.

**Official docs:** https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html

### SQS - Managed queue

**What it does:** A durable message queue that decouples request/response APIs from slower background work. Consumers delete messages only after success.

**Console path:** SQS -> Queues -> Send/receive messages -> Monitoring -> Dead-letter queue.

**CLI:**
```bash
aws sqs list-queues
aws sqs send-message --queue-url URL --message-body '{"import_id":"demo"}'
aws sqs receive-message --queue-url URL --wait-time-seconds 20
```

**First tiny step:** Create a tiny queue, send one JSON message, receive it, then delete it after reading.

**Beginner trap:** Deleting messages before work succeeds; ignoring duplicate delivery and idempotency; no DLQ.

**Project context:** FastAPI creates import jobs; Go worker long-polls SQS, processes XLSX from S3, updates PostgreSQL.

**Official docs:** https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-getting-started.html

## Identity & Security

### IAM - Users, roles, policies

**What it does:** Controls who and what can access AWS resources. Roles are preferred over long-lived access keys for services and CI/CD.

**Console path:** IAM -> Users, Roles, Policies, Identity Providers.

**CLI:**
```bash
aws sts get-caller-identity
aws iam list-roles --output table
```

**First tiny step:** Always run sts get-caller-identity before experiments. Know which account and role you are using.

**Beginner trap:** Using AdministratorAccess everywhere or storing long-lived access keys in apps and GitHub.

**Project context:** EC2/ECS roles access S3/CloudWatch without hardcoded credentials.

**Official docs:** https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html

### Cognito - Managed app authentication

**What it does:** Managed user pools and OAuth/OIDC flows for sign-in. Authentication says who the user is; your backend still enforces authorization.

**Console path:** Cognito -> User Pools -> App clients -> Hosted UI.

**CLI:**
```bash
aws cognito-idp list-user-pools --max-results 10
```

**First tiny step:** Defer until backend RBAC rules are already working locally.

**Beginner trap:** Thinking Cognito replaces role-based access control. It does not decide which campaigns a manager can see.

**Project context:** Possible later login layer for dashboard users; FastAPI still filters data by role/scope.

**Official docs:** https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html

### Secrets Manager - Secrets with lifecycle

**What it does:** Stores sensitive values such as database passwords and API keys, with optional rotation workflows.

**Console path:** Secrets Manager -> Secrets.

**CLI:**
```bash
aws secretsmanager list-secrets
```

**First tiny step:** Use later for real secrets. For early config, SSM Parameter Store may be simpler.

**Beginner trap:** Putting every config value in Secrets Manager and paying for secret/API usage unnecessarily.

**Project context:** Store DB password and external API credentials in later production-shaped deployments.

**Official docs:** https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html

### SSM Parameter Store - Configuration and simple secrets

**What it does:** Stores configuration values and some secrets in a hierarchical path structure.

**Console path:** Systems Manager -> Parameter Store.

**CLI:**
```bash
aws ssm describe-parameters
aws ssm get-parameter --name /dashboard/dev/app_env
```

**First tiny step:** Use it to store non-sensitive environment config before full secret rotation matters.

**Beginner trap:** Treating non-secret config as harmless. Permissions still matter.

**Project context:** Store app environment, feature flags, and simple deployment settings.

**Official docs:** https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html

### S3 Bucket Policies - Resource permissions

**What it does:** Policies attached to S3 buckets that define who can read, write, or list objects. Usually combined with IAM roles.

**Console path:** S3 -> Bucket -> Permissions -> Bucket policy and Block Public Access.

**CLI:**
```bash
aws s3api get-public-access-block --bucket BUCKET
aws s3api get-bucket-policy --bucket BUCKET
```

**First tiny step:** Confirm Block Public Access is on before any upload project.

**Beginner trap:** Making a bucket public for convenience instead of using IAM roles or pre-signed URLs.

**Project context:** Private XLSX uploads must never be publicly readable by default.

**Official docs:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html

## Observability & Cost

### CloudWatch Logs - Centralized logs

**What it does:** Stores application and service logs so you can debug without SSHing into every machine.

**Console path:** CloudWatch -> Log Groups -> Log Streams -> Logs Insights.

**CLI:**
```bash
aws logs describe-log-groups --output table
aws logs tail LOG_GROUP --follow
```

**First tiny step:** Send one app log stream and tail it from CLI.

**Beginner trap:** Forgetting retention. Logs can accumulate cost quietly.

**Project context:** FastAPI request errors, import events, and Go worker errors should land here.

**Official docs:** https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_GettingStarted.html

### CloudWatch Metrics and Alarms - Signals and alerts

**What it does:** Metrics track resource/application behavior; alarms notify when thresholds are crossed.

**Console path:** CloudWatch -> Metrics, Alarms, Dashboards.

**CLI:**
```bash
aws cloudwatch describe-alarms --output table
```

**First tiny step:** Create one simple alarm only after you understand what metric it watches.

**Beginner trap:** Alerting on everything and ignoring all alarms. Start with few meaningful alarms.

**Project context:** ALB 5xx errors, RDS CPU/storage, SQS queue age, worker failures.

**Official docs:** https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html

### AWS Budgets - Spend alerts

**What it does:** Budget alerts notify you when estimated or actual spend crosses thresholds. It is a guardrail, not an automatic kill switch.

**Console path:** Billing and Cost Management -> Budgets.

**CLI:**
```bash
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text)
```

**First tiny step:** Create a small monthly budget before any EC2/RDS/ALB/NAT experiment.

**Beginner trap:** Setting it after surprise cost happens. It should be day-zero setup.

**Project context:** Protect AWS credits while learning. Put budget screenshots in portfolio notes.

**Official docs:** https://www.wellarchitectedlabs.com/cost-optimization/

### Cost Explorer - Cost analysis

**What it does:** Shows cost by service, tag, account, and time. Best for understanding which services are costing money.

**Console path:** Billing and Cost Management -> Cost Explorer.

**CLI:**
```bash
aws ce get-cost-and-usage --time-period Start=YYYY-MM-DD,End=YYYY-MM-DD --granularity MONTHLY --metrics UnblendedCost
```

**First tiny step:** Use the console first. The charts are easier than CLI for early learning.

**Beginner trap:** Only checking cost at the end of the month. Check weekly during experiments.

**Project context:** Use tags like Project=marketing-dashboard and Environment=dev to attribute spend.

**Official docs:** https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html

## CI/CD & IaC

### GitHub Actions - CI/CD workflows

**What it does:** Runs tests, builds containers, and triggers deploy steps when code changes.

**Console path:** GitHub repo -> Actions tab -> Workflow runs and logs.

**CLI:**
```bash
# In workflow after AWS auth:
aws sts get-caller-identity
```

**First tiny step:** Start with pytest/ruff only. Add AWS deployment after the manual deploy is understood.

**Beginner trap:** Building a deploy pipeline before you know how to deploy manually.

**Project context:** On push: run tests, build image, push to ECR, deploy to EC2/ECS later.

**Official docs:** https://docs.github.com/actions/writing-workflows/quickstart

### GitHub Actions OIDC to AWS - Short-lived deploy identity

**What it does:** Allows GitHub Actions to assume an AWS IAM role without storing long-lived AWS access keys.

**Console path:** IAM -> Identity Providers and Roles -> Trust relationships.

**CLI:**
```bash
# From a workflow using aws-actions/configure-aws-credentials:
aws sts get-caller-identity
```

**First tiny step:** Read the trust policy carefully before granting deploy permissions.

**Beginner trap:** Putting AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in GitHub Secrets.

**Project context:** Safer CI/CD deploy to AWS for your portfolio project.

**Official docs:** https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services

### Terraform - Infrastructure as Code

**What it does:** Defines infrastructure as code. You review changes with plan, apply intentionally, and destroy experiments when done.

**Console path:** AWS Console is used to verify what Terraform created, not as the long-term control plane.

**CLI:**
```bash
terraform init
terraform plan
terraform apply
terraform destroy
```

**First tiny step:** Use Terraform only for resources you can already recognize in the console and describe with CLI.

**Beginner trap:** Copy-pasting Terraform that creates expensive resources you cannot explain or clean up.

**Project context:** Codify VPC, EC2, RDS, S3, IAM, ALB, ECS only after manual/CLI learning.

**Official docs:** https://developer.hashicorp.com/terraform/tutorials/aws-get-started

## Optional Analytics

### QuickSight - Managed BI dashboards

**What it does:** AWS business intelligence service for dashboards and reports. Useful as a comparison to your custom React dashboard, not as the first build target.

**Console path:** QuickSight console -> Datasets, analyses, dashboards.

**CLI:**
```bash
aws quicksight list-dashboards --aws-account-id ACCOUNT_ID
```

**First tiny step:** Use later to compare build-vs-buy BI experiences.

**Beginner trap:** Replacing the custom dashboard too early and losing backend/RBAC/API learning value.

**Project context:** Optional: compare QuickSight dashboard from the same clean data model.

**Official docs:** https://docs.aws.amazon.com/quicksight/latest/user/welcome.html

### Athena - Query S3 with SQL

**What it does:** Serverless SQL query engine for data stored in S3. Useful for data lake experiments.

**Console path:** Athena -> Query editor -> Workgroups.

**CLI:**
```bash
aws athena start-query-execution --query-string "SELECT 1" --work-group primary
```

**First tiny step:** Defer until you have stable S3 data and know why PostgreSQL is not the right query layer.

**Beginner trap:** Scanning large S3 data unnecessarily. Athena cost depends on data scanned.

**Project context:** Later: query historical exports or raw cleaned files in S3.

**Official docs:** https://docs.aws.amazon.com/athena/latest/ug/what-is.html

### Glue - Data catalog and ETL

**What it does:** Data catalog and ETL service. Helps organize datasets for Athena and data pipelines.

**Console path:** AWS Glue -> Data Catalog, Crawlers, ETL jobs.

**CLI:**
```bash
aws glue get-databases
```

**First tiny step:** Defer. It is data engineering infrastructure, not needed for the first dashboard.

**Beginner trap:** Adding ETL infrastructure before the XLSX schema and PostgreSQL model are stable.

**Project context:** Optional BI/data-lake extension if dashboard evolves into analytics platform.

**Official docs:** https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html

## Tutorial Links

- [AWS CLI Getting Started](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)
- [AWS CloudShell User Guide](https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html)
- [AWS Hands-on Tutorials](https://aws.amazon.com/getting-started/hands-on/)
- [AWS Skill Builder](https://aws.amazon.com/training/)
- [Amazon EC2 Getting Started](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html)
- [S3 Getting Started](https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html)
- [RDS PostgreSQL Getting Started](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html)
- [CloudWatch Logs Getting Started](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_GettingStarted.html)
- [SQS Developer Guide](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-getting-started.html)
- [ECS Workshop](https://ecsworkshop.com/)
- [EKS Workshop](https://www.eksworkshop.com/)
- [Terraform AWS Tutorials](https://developer.hashicorp.com/terraform/tutorials/aws-get-started)

## AI Coding Agent Prompt

```text
Use this AWS field guide as context. Do not build all AWS services at once. Start by making the local FastAPI/PostgreSQL app work, then add exactly one infrastructure concept at a time. For each change, update docs/DECISIONS.md, docs/CLI_RUNBOOK.md, docs/COST_NOTES.md, and docs/CLEANUP.md. Prefer console understanding first, CLI inspection second, Terraform only after the resource is understood. Keep the marketing dashboard examples small: XLSX import, PostgreSQL normalized rows, role-based access, S3 raw uploads, CloudWatch logs, and only later SQS + Go worker or Valkey if a real need appears.
```
