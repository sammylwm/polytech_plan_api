import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deadlines', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeadlineAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to='deadline-attachments/')),
                ('name', models.CharField(max_length=255)),
                ('size', models.PositiveBigIntegerField()),
                ('deadline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='deadlines.deadline')),
            ],
        ),
    ]
