
import boto3
import sys
from botocore.exceptions import ClientError

USER_POOL_ID = "us-east-1_3n4C8QOve"

def create_user_with_group(username, password, email, group_name):

    cognito = boto3.client('cognito-idp')

    try:
        print(f"🛠️  Creando usuario: {username}...")
        cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,
            TemporaryPassword=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'email_verified',
                    'Value': 'true'
                }
            ],
            MessageAction='SUPPRESS'
        )
        print(f"✅ Usuario '{username}' creado exitosamente.")

        print(f"🔒 Estableciendo contraseña permanente...")
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username,
            Password=password,
            Permanent=True
        )
        print(f"✅ Contraseña establecida permanentemente.")

        print(f"👤 Agregando usuario al grupo '{group_name}'...")
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        print(f"✅ Usuario '{username}' agregado a '{group_name}'.")

        print(f"\n🎉 ¡Éxito! Usuario '{username}' está listo y en el grupo '{group_name}'.")

    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            print(f"❌ Error: El usuario '{username}' ya existe.")
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"❌ Error: El grupo '{group_name}' no existe. Por favor, créalo primero en la consola de Cognito.")
        elif e.response['Error']['Code'] == 'InvalidPasswordException':
            print(f"❌ Error: La contraseña no cumple con los requisitos de seguridad de tu User Pool.")
        else:
            print(f"❌ Error inesperado: {e}")
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("❌ Error: Se requieren 4 argumentos.")
        print("  python3 create_user.py cliente.nuevo 'P@ssword123!' cliente.nuevo@email.com clientes")
        print("\nEjemplo para un admin:")
        print("  python3 create_user.py admin.nuevo 'AdminP@ss123!' admin.nuevo@email.com admin")
        print("\n❗️IMPORTANTE: Si tu contraseña tiene un * u otro símbolo, ¡ponla entre comillas simples ('')!")
        sys.exit(1)

    user_param = sys.argv[1]
    pass_param = sys.argv[2]
    email_param = sys.argv[3]
    group_param = sys.argv[4]

    create_user_with_group(user_param, pass_param, email_param, group_param)

    ## admin.jav,SuperP@ss123!

    # python3 crearusuario.py admin.jav 'SuperP@ss123!' admin.nuevo@meddisupply.com admin
    # python3 crearusuario.py cliente.pedro 'ClienteP@ss123!' pedro.perez@meddisupply.com clientes


# python3 crearusuario.py cliente.juan 'SuperP@ss123!' pedro1.perez@meddisupply.com clientes