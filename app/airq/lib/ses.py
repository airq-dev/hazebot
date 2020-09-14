import boto3
import logging
import typing

from airq import config


logger = logging.getLogger(__name__)


def send_email(to_addresses: typing.List[str], subject: str, body: str) -> bool:
    ses = boto3.client(
        'ses',
        region_name=config.SES_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
    )

    try:
        ses.send_email(
            Source=config.SES_EMAIL_SOURCE,
            Destination={'ToAddresses': to_addresses},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': body}
                }
            }
        )
    except Exception as e:
        logger.warning("Failed to send email to %s: %s", to_addresses, str(e))
        return False

    return True
