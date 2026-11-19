import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deadlines', '0002_deadlineattachment'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('semester', models.CharField(max_length=6)),
                ('subject', models.CharField(max_length=200)),
                ('text', models.TextField()),
                ('due_date', models.DateField(blank=True, null=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='session_tasks', to='deadlines.group')),
            ],
        ),
    ]
