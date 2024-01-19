class UniqueIds:
    def __init__(self):
        self.shoko_aid = 0
        self.shoko_eid = 0
        self.anidb_id = 0
        self.tvdb_id = 0

    def get_dict(self):
        ids = dict()
        if self.shoko_aid != 0:
            ids['shoko_aid'] = str(self.shoko_aid)
        if self.shoko_eid != 0:
            ids['shoko_eid'] = str(self.shoko_eid)
        if self.anidb_id != 0:
            ids['anidb'] = str(self.anidb_id)
        if self.tvdb_id != 0:
            ids['tvdb'] = str(self.tvdb_id)

        return ids
