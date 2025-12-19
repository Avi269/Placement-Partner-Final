"""Django management command to seed learning resources"""
from django.core.management.base import BaseCommand
from core.models import LearningResource

class Command(BaseCommand):
    help = 'Seed learning resources database'

    def handle(self, *args, **options):
        resources = [
            # Python resources
            {
                "skill": "python",
                "title": "Python.org Official Tutorial",
                "url": "https://docs.python.org/3/tutorial/",
                "resource_type": "tutorial",
                "description": "Comprehensive introduction to Python by the core team.",
                "duration": "10-15 hours",
                "priority": 100
            },
            # Add more resources...
        ]
        
        for res_data in resources:
            LearningResource.objects.update_or_create(
                skill=res_data['skill'],
                title=res_data['title'],
                defaults=res_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(resources)} resources'))