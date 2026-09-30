from django.db import migrations, models


def add_address_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, "accounts_veterinaireprofile"
            )
        }
    if "address" in columns:
        return
    schema_editor.execute(
        "ALTER TABLE accounts_veterinaireprofile "
        "ADD COLUMN address varchar(255) NOT NULL DEFAULT ''"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_photo"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="veterinaireprofile",
                    name="address",
                    field=models.CharField(blank=True, max_length=255),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_address_if_missing, migrations.RunPython.noop),
            ],
        ),
    ]
