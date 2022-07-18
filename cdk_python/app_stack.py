from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_rds as rds,
    Duration
)
from constructs import Construct
from .vpc_stack import vpcStack


class AppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, three_tier=True, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Attempt to get custom cidr from context if provided
        context_cidr = self.node.try_get_context("cidr")

        # Creating the networking resources
        network = vpcStack(self, 'vpc', three_tier=three_tier, vpc_cidr=context_cidr if context_cidr else '10.0.0.0/16')

        
        asg_role = iam.Role(self, "MyRole",
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
            )         
        asg_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2RoleforSSM"))

        asg = autoscaling.AutoScalingGroup(self, "ASG",
                vpc=network.vpc,
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
                machine_image=ec2.GenericLinuxImage({'us-east-1':'ami-0cff7528ff583bf9a'}),
                security_group=network.asg_sg,
                cooldown=Duration.minutes(1),
                key_name='n-virginia-nedranboss',
                min_capacity=2,
                max_capacity=8,
                role=asg_role,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                user_data=ec2.UserData.custom(
                '''
                #!/bin/bash
                sudo yum update -y
                sudo yum install -y httpd.x86_64
                sudo yum install -y amazon-cloudwatch-agent
                sudo systemctl start httpd
                sudo systemctl enable httpd
                sudo systemctl start amazon-ssm-agent
                sudo su
                sudo chmod 755 -R /var/www/html
                sudo echo "hello world from $(hostname -f)" >> /var/www/html/index.html
                '''
                )
            )

        bastion = ec2.BastionHostLinux(self, "BastionHost",
                vpc=network.vpc,
                key_name='n-virginia-nedranboss',
                security_group=network.bastion_sg,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
            )
        
        # Configure load balancer
        lb = elbv2.ApplicationLoadBalancer(self, "LB",
                vpc=network.vpc,
                internet_facing=True,
                security_group=network.lb_sg
            )
        
        listener = lb.add_listener("Listener",
                    port=80
            )

        listener.add_targets("ApplicationFleet",
            port=80,
            targets=[asg]
            )

        if three_tier:
            # in case a three tier architecture is specified, create a database and a
            # secrets manager secret, and grants get secret value role to the 
            # application fleet
            db_secrets = rds.DatabaseSecret(self, 'postgres-secret',
                        username='postgres',
                        secret_name='postgres-credentials'
                        )

            db = rds.DatabaseInstance(self, "db",
                        engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_13_4),
                        instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
                        credentials=rds.Credentials.from_secret(db_secrets),
                        vpc=network.vpc,
                        multi_az=True,
                        security_groups=[network.db_SG],
                        vpc_subnets=ec2.SubnetSelection(
                            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                        )
                        )

            asg.add_to_role_policy(iam.PolicyStatement(
                resources=[db_secrets.secret_arn],
                actions=[
                        "secretsmanager:GetSecretValue"]
                ))

        
    
