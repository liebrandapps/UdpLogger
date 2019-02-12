from configparser import RawConfigParser


class Config:


    def __init__(self, cfgFile):
        self.cfg = RawConfigParser()
        if cfgFile is not None:
            _ = self.cfg.read(cfgFile)
        self.scope = {}
        self.lastget = None

    def addScope(self, dictionary):
        for key in dictionary.keys():
            if key in self.scope.keys():
                self.scope[key].update(dictionary[key])
            else:
                self.scope[key] = dictionary[key]

    #
    # name is section_option
    def __getattr__(self, name):
        if self.lastget is None:
            idx = name.split('_')
            if len(idx) > 1:
                # if we have more than one '_' in the string, section_option may be ambiguous
                tmpSection = idx[0]
                if tmpSection not in self.scope and len(idx)>2:
                    tmpSection = idx[0] + "_" + idx[1]
                    idx[1] = "_".join(idx[2:])
                else:
                    idx[1] = "_".join(idx[1:])
                if tmpSection in self.scope:
                    option = idx[1]
                    subScope = self.scope[tmpSection]
                    if option in subScope:
                        tuple = subScope[option]
                        if len(tuple) > 1:
                            defaultValue = [] if tuple[0].upper().startswith('A') else tuple[1]
                        else:
                            defaultValue = [] if tuple[0].upper().startswith('A') else None
                        if not(self.cfg.has_option(tmpSection, option)):
                            return defaultValue
                        if tuple[0].startswith('S'):
                            return self.cfg.get(tmpSection, option)
                        if tuple[0].startswith('I'):
                            return self.cfg.getint(tmpSection, option)
                        if tuple[0].startswith('B'):
                            return self.cfg.getboolean(tmpSection, option)
                        if tuple[0].upper().startswith('A'):
                            return [] if self.cfg.get(tmpSection, option) is None else self.cfg.get(tmpSection, option).split(':')
        return None

