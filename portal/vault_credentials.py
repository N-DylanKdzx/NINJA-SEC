"""Read the MySQL application credential from OCI Vault without printing it."""

import argparse
import base64
import json
from pathlib import Path

import oci


def read_mysql_credentials(secret_ocid, profile=None):
    if not secret_ocid.startswith('ocid1.vaultsecret.'):
        raise ValueError('Se requiere un OCID de secreto de OCI Vault.')
    if profile is None:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        config = {'region': signer.region}
    else:
        config = oci.config.from_file(profile_name=profile)
        token = Path(config['security_token_file']).read_text().strip()
        key = oci.signer.load_private_key_from_file(config['key_file'])
        signer = oci.auth.signers.SecurityTokenSigner(token, key)
    client = oci.secrets.SecretsClient(config, signer=signer, timeout=(5, 10))
    bundle = client.get_secret_bundle(secret_ocid, stage='CURRENT').data
    value = json.loads(base64.b64decode(bundle.secret_bundle_content.content, validate=True))
    if not isinstance(value, dict) or not all(
        isinstance(value.get(field), str) and value[field] for field in ('username', 'password')
    ):
        raise ValueError('El secreto debe contener username y password.')
    return value['username'], value['password']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('secret_ocid')
    parser.add_argument('--profile', help='Perfil OCI con sesión temporal. En OCI se usa la identidad de la instancia por defecto.')
    args = parser.parse_args()
    read_mysql_credentials(args.secret_ocid, args.profile)
    print('Secreto CURRENT accesible y válido.')
