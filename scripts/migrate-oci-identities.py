"""Keep original and staged identities in their existing least-privilege groups."""
import oci

def main():
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM');co=oci.core.ComputeClient(cfg);iam=oci.identity.IdentityClient(cfg)
    instances=oci.pagination.list_call_get_all_results(co.list_instances,cfg['tenancy']).data
    new={role:next(x.id for x in instances if x.display_name=='ninjasec-'+role+'-stable-01' and x.lifecycle_state in ('RUNNING','PROVISIONING','STARTING')) for role in ['utility','replica']}
    utility=['ocid1.instance.oc1.iad.anuwcljt3nxgmgacays7ij4hje7tqwebsgo6wm3mkpwy2cl3veji2ncwaaea',new['utility']]
    replica=['ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla',new['replica']]
    groups={'ninjasec-grafana-instance':utility,'ninjasec-grafana-replica-reader':replica,'ninjasec-recovery-instances':utility+replica}
    for group in iam.list_dynamic_groups(cfg['tenancy']).data:
        if group.name not in groups:continue
        response=iam.get_dynamic_group(group.id)
        rule='ANY {'+', '.join("instance.id = '"+id+"'" for id in groups[group.name])+'}'
        iam.update_dynamic_group(group.id,oci.identity.models.UpdateDynamicGroupDetails(matching_rule=rule),if_match=response.headers['etag'])
        print('MIGRATION_IDENTITY',group.name,groups[group.name],flush=True)

if __name__=='__main__':main()
