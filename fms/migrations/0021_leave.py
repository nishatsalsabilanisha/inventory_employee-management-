from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fms', '0020_remove_paymenttransaction_supplier_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Leave',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leave_type', models.CharField(choices=[('Casual', 'Casual'), ('Sick', 'Sick'), ('Annual', 'Annual')], max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending', max_length=20)),
                ('applied_on', models.DateTimeField(auto_now_add=True)),
                ('admin_remarks', models.TextField(blank=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leaves', to='fms.employeeprofile')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
            ],
        ),
    ]