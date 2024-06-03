from data.asvttk_service.database import ASVTTKDatabase


class ASVTTKServiceImpl:
    def __init__(self, db: ASVTTKDatabase):
        self.db = db

