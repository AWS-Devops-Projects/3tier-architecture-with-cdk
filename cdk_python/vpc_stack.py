from aws_cdk import (
    Stack,
    aws_ec2 as ec2
)
from constructs import Construct


class vpcStack(Construct):

    def __init__(self, scope: Construct, construct_id: str, vpc_cidr='10.0.0.0/16', three_tier=True,**kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        ''' AWS CDK Construct that creates a configurable VPC for hosting a three tier architecture'''
        if three_tier:
            self.vpc = ec2.Vpc(
                    self, 'vpc',
                    cidr=vpc_cidr,
                    max_azs=2,
                    nat_gateways=2,
                    enable_dns_hostnames=True,
                    enable_dns_support=True,
                    subnet_configuration=[
                        ec2.SubnetConfiguration(
                            name= 'load_balancer',
                            subnet_type= ec2.SubnetType.PUBLIC,
                            cidr_mask= 24
                        ),
                        ec2.SubnetConfiguration(
                            name= 'application',
                            subnet_type= ec2.SubnetType.PRIVATE_WITH_NAT,
                            cidr_mask= 24
                        ), 
                        ec2.SubnetConfiguration(
                            name= 'database',
                            subnet_type= ec2.SubnetType.PRIVATE_ISOLATED,
                            cidr_mask= 24
                        )
                    ]
                )
        else: 
            self.vpc = ec2.Vpc(
                    self, 'vpc',
                    cidr=vpc_cidr,
                    max_azs=2,
                    nat_gateways=2,
                    enable_dns_hostnames=True,
                    enable_dns_support=True,
                    subnet_configuration=[
                        ec2.SubnetConfiguration(
                            name= 'load_balancer',
                            subnet_type= ec2.SubnetType.PUBLIC,
                            cidr_mask= 24
                        ),
                        ec2.SubnetConfiguration(
                            name= 'application',
                            subnet_type= ec2.SubnetType.PRIVATE_WITH_NAT,
                            cidr_mask= 24
                        )
                    ]
                )
                
        
        # Load balancer security group
        self.lb_sg = ec2.SecurityGroup(
            self, 'lb-SG',
            vpc=self.vpc,
            allow_all_outbound=True
        )

        self.lb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443)
        )

        self.lb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80)
        )


        # Bastion security group
        self.bastion_sg = ec2.SecurityGroup(
            self, 'bastion-SG',
            vpc=self.vpc,
            allow_all_outbound=True
        )

        self.bastion_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22)
        )

        # Application layer security group
        self.asg_sg = ec2.SecurityGroup(
            self, 'asg-SG',
            vpc=self.vpc,
            allow_all_outbound=True
        )

        self.asg_sg.add_ingress_rule(
            self.lb_sg,
            ec2.Port.tcp(443)
        )

        self.asg_sg.add_ingress_rule(
            self.lb_sg,
            ec2.Port.tcp(80)
        )

        self.asg_sg.add_ingress_rule(
            self.bastion_sg,
            ec2.Port.tcp(22)
        )

        # Database security group if three tier is specified
        if three_tier:
            self.db_SG = ec2.SecurityGroup(
                self, 'db-SG',
                vpc=self.vpc,
                allow_all_outbound=True
            )

            self.db_SG.add_ingress_rule(
                self.asg_sg,
                ec2.Port.tcp(5432)
            )



