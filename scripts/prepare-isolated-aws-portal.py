import boto3, io, json, pathlib, sys, tarfile
repo, archive, config = [pathlib.Path(x) for x in sys.argv[1:4]]
if len(sys.argv) == 5:
    state = json.loads(pathlib.Path(sys.argv[4]).read_text())
    def read(resource_type):
        [row] = [r for r in state['resources'] if r['mode']=='managed'
                 and r.get('module')=='module.aws_infra' and r['type']==resource_type]
        [instance] = row['instances']
        return instance['attributes']
    vpc = read('aws_vpc')
    if vpc['cidr_block'] != '10.243.0.0/16' or vpc['tags']['Name'] != 'ninjasec-iac-service-demo':
        raise ValueError('Refusing cleanup inputs from another environment')
    launch = read('aws_launch_template')
    profile_name = launch['iam_instance_profile'][0]['name']
    role = json.loads(read('aws_vpc_endpoint')['policy'])['Statement'][0]['Principal']['AWS']
    cert = read('aws_lb_listener')['certificate_arn']
    image = launch['image_id']
else:
    session = boto3.Session(region_name='us-east-1')
    assert session.client('sts').get_caller_identity()['Account']=='533267256700'
    profile = session.client('iam').get_instance_profile(InstanceProfileName='LabInstanceProfile')['InstanceProfile']
    profile_name = profile['InstanceProfileName']
    role = session.client('lambda').get_function_configuration(FunctionName='ninjasec-export-cloudtrail')['Role']
    certs = session.client('acm').list_certificates(CertificateStatuses=['ISSUED'])['CertificateSummaryList']
    cert = next(x['CertificateArn'] for x in certs if x['DomainName']=='portal-aws.ninjasec.dev')
    image = 'ami-08b275ac6cc5dbefb'
with tarfile.open(archive, 'w:gz') as pkg:
    for name in ('app.py','vault_credentials.py','requirements.txt','schema.sql','portal.js','login.js','portal.css','login.html','index.html'):
        pkg.add(repo / 'portal' / name, arcname=name)
    bootstrap = (repo / 'scripts' / 'bootstrap-aws-app.sh').read_text(encoding='utf-8')
    bootstrap = bootstrap.replace('/ninjasec/', '/ninjasec-iac-service-demo/')
    bootstrap = bootstrap.replace('NINJA-SEC/Host', 'NINJA-SEC/IaCReplay').encode()
    member = tarfile.TarInfo('replay-bootstrap.sh')
    member.size = len(bootstrap)
    member.mode = 0o644
    pkg.addfile(member, io.BytesIO(bootstrap))
config.write_text(json.dumps({
    'enable_service_demo': True,
    'demo_ami_id':image,
    'portal_replay': {'instance_profile':profile_name,'instance_role_arn':role,'certificate_arn':cert,'archive_path':str(archive)}
}), encoding='utf-8')
print(role)

