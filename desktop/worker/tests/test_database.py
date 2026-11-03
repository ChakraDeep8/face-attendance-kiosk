import tempfile, unittest
from pathlib import Path
import numpy as np
from app.database import Repository

class RepositoryTests(unittest.TestCase):
    def test_person_templates_and_event_cooldown(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=Repository(Path(folder)/"test.db")
            vector=np.ones(512,dtype=np.float32); vector/=np.linalg.norm(vector)
            person=repo.save_person("Test User","EMP-1","face.jpg",[vector.tolist()])
            self.assertEqual(1,len(repo.people()))
            self.assertEqual(1,len(repo.template_index()))
            repo.add_event("Authorized",person,"Test User",99.0,"Webcam")
            self.assertTrue(repo.recent_event(person,"Authorized",60))

if __name__=="__main__": unittest.main()
