import tempfile, unittest
from pathlib import Path
import numpy as np
from app.database import Repository
from app.monitor import Monitor

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

    def test_crossing_geometry_and_zone(self):
        line=(0,100,200,100)
        self.assertLess(Monitor._side((50,80),line)*Monitor._side((50,120),line),0)
        self.assertTrue(Monitor._inside((50,50),(10,10,90,90)))
        self.assertFalse(Monitor._inside((100,50),(10,10,90,90)))

if __name__=="__main__": unittest.main()
