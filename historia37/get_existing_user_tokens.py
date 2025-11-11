
import sys

import boto3


def get_access_token(username, password):
    USER_POOL_ID = "us-east-1_3n4C8QOve"
    CLIENT_ID = "113qhpd3hktvupdbhpi5361h90"

    cognito = boto3.client('cognito-idp')

    try:
        auth_response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )

        access_token = auth_response['AuthenticationResult']['AccessToken']
        return access_token

    except Exception as e:
        print(f"❌ Error obteniendo token para {username}: {e}")
        return None


def generar_curl_para_usuario(username, password):
    access_token = get_access_token(username, password)

    if access_token:
        curl_command = (
            f"# Comando curl para el usuario: {username}\n"
            f"curl -H \"Authorization: Bearer {access_token}\" \\\n"
            f"     -H \"X-Test-IP: 190.14.255.110\" \\\n"
            f"     -H \"Content-Type: application/json\" \\\n"
            f"     -X POST \\\n"
            f"     -d '{{\"vendor_id\":\"v1\",\"period\":\"trimestral\",\"start_date\":\"2025-01-01\",\"end_date\":\"2025-03-31\"}}' \\\n"
            f"     https://r1kyo276f3.execute-api.us-east-1.amazonaws.com/prod/reports/sales-report"
        )

        return curl_command

    else:
        return f"# No se pudo generar el curl para {username}. (Revisar error de token arriba)"

if __name__ == "__main__":

    if len(sys.argv) == 3:
        user_param = sys.argv[1]
        pass_param = sys.argv[2]

        curl_para_probar = generar_curl_para_usuario(user_param, pass_param)

        print(curl_para_probar)

    else:
        print("Uso: python3 get_existing_user_tokens.py <username> <password>")
        print("Ejemplo: python3 este_script.py pruebassadmin 'Corinna2019*'")

        # python3 get_existing_user_tokens.py get cliente.pedro 'ClienteP@ss123!'

#python3 get_existing_user_tokens.py cliente.juan 'SuperP@ss123!' cliente.juan 'SuperP@ss123!'

