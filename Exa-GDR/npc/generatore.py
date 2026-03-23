"""
npc/generatore.py — Generatore casuale di NPC e Nemici
"""
import random

# ── Nomi ─────────────────────────────────────────────────────────────────────

NOMI_IT = {
    "umano_m":   ["Aldric","Beren","Caius","Dario","Edric","Fausto","Garan",
                  "Hadrian","Ilvar","Jorin","Kael","Loras","Maren","Norvin",
                  "Oswin","Peran","Quinn","Rolan","Soren","Taran","Ulric","Valen"],
    "umano_f":   ["Aelindra","Brynn","Celia","Dara","Elara","Fiona","Gwyn",
                  "Hana","Ilara","Jora","Kira","Lena","Mira","Nora","Orla",
                  "Pella","Rhea","Sera","Tara","Una","Vera","Wren"],
    "elfo_m":    ["Aelion","Caladrel","Erevan","Farandel","Gaelion","Halamar",
                  "Ithilion","Jariel","Kyrandel","Lathiel","Miravel","Narandel"],
    "elfo_f":    ["Aelindra","Caladria","Erindel","Faralei","Gaelindra","Halavar",
                  "Ithilara","Jarindra","Kyranel","Lathara","Miravar","Narindra"],
    "nano_m":    ["Aldur","Balin","Dolgrin","Durgal","Gimrak","Gorin","Harbek",
                  "Kildrak","Morgran","Orsik","Rangrim","Thordin","Umkar","Veit"],
    "nano_f":    ["Amber","Artin","Audhild","Dagnal","Diesa","Eldeth","Gunnloda",
                  "Gurdis","Helja","Hlin","Kathra","Kristryd","Mardred","Riswynn"],
    "halfling_m":["Alton","Ander","Cade","Corrin","Eldon","Garret","Lyle","Merric",
                  "Milo","Osborn","Perrin","Reed","Roscoe","Wellby"],
    "halfling_f":["Andry","Bree","Callie","Cora","Euphemia","Jillian","Kithri",
                  "Lavinia","Lidda","Merla","Nedda","Paela","Portia","Seraphina"],
    "mostro":    ["Grax","Zorgar","Malgoth","Vrak","Skrix","Thrax","Gorguk",
                  "Malvok","Dreznak","Krix","Vulgrak","Skorn","Morzug","Threx"],
}

COGNOMI_IT = ["Alidori","Brasero","Calmieri","Devori","Fieramonti","Gabbiani",
              "Lupetti","Moretti","Neri","Orlandini","Palumbo","Romani","Sordi",
              "Torrini","Uberti","Valenti","Zanetti","Ferretti","Bianchi","Russo",
              "Conti","Mancini","Costa","Amato","Greco","Lombardi","Martinelli"]

NOMI_EN = {
    "umano_m":   ["Aldric","Beren","Caius","Drake","Edmund","Finn","Gareth",
                  "Hadrian","Ivan","Jared","Kane","Leon","Marcus","Nathan",
                  "Owen","Percival","Quinn","Roland","Seth","Torin","Uther","Viktor"],
    "umano_f":   ["Aelindra","Brynn","Clara","Diana","Elena","Fiona","Grace",
                  "Helena","Iris","Julia","Kira","Luna","Mira","Nora","Olivia",
                  "Petra","Rhea","Sara","Tara","Una","Vera","Wren"],
    "elfo_m":    ["Aelion","Caladrel","Erevan","Farandel","Gaelion","Halamar",
                  "Ithilion","Jariel","Kyrandel","Lathiel","Miravel","Narandel"],
    "elfo_f":    ["Aelindra","Caladria","Erindel","Faralei","Gaelindra","Halavar",
                  "Ithilara","Jarindra","Kyranel","Lathara","Miravar","Narindra"],
    "nano_m":    ["Aldur","Balin","Dolgrin","Durgal","Gimrak","Gorin","Harbek",
                  "Kildrak","Morgran","Orsik","Rangrim","Thordin","Umkar","Veit"],
    "nano_f":    ["Amber","Artin","Audhild","Dagnal","Diesa","Eldeth","Gunnloda",
                  "Gurdis","Helja","Hlin","Kathra","Kristryd","Mardred","Riswynn"],
    "halfling_m":["Alton","Ander","Cade","Corrin","Eldon","Garret","Lyle","Merric",
                  "Milo","Osborn","Perrin","Reed","Roscoe","Wellby"],
    "halfling_f":["Andry","Bree","Callie","Cora","Euphemia","Jillian","Kithri",
                  "Lavinia","Lidda","Merla","Nedda","Paela","Portia","Seraphina"],
    "mostro":    ["Grax","Zorgar","Malgoth","Vrak","Skrix","Thrax","Gorguk",
                  "Malvok","Dreznak","Krix","Vulgrak","Skorn","Morzug","Threx"],
}

COGNOMI_EN = ["Ashford","Blackwood","Coldwater","Darkmore","Eaglestone","Fairwind",
              "Goldbrook","Highhill","Ironforge","Jadestone","Kingswood","Lightfall",
              "Moorland","Nighthollow","Oakenshield","Proudmoore","Queensway",
              "Riverstone","Shadowmere","Thornwood","Underhill","Valewind","Wolfcrest"]

RAZZE_IT = ["Umano","Elfo","Nano","Halfling","Mezzorco","Tiefling","Draconico","Gnomo"]
RAZZE_EN = ["Human","Elf","Dwarf","Halfling","Half-orc","Tiefling","Dragonborn","Gnome"]

CLASSI_NPC_IT  = ["Mercante","Guardia","Contadino","Chierico","Saggio","Ladro",
                   "Bardo","Artigiano","Soldato","Nobile","Pescatore","Cacciatore"]
CLASSI_NPC_EN  = ["Merchant","Guard","Farmer","Cleric","Sage","Thief",
                   "Bard","Craftsman","Soldier","Noble","Fisherman","Hunter"]

TIPI_NEMICO_IT = ["Goblin","Orco","Scheletro","Zombie","Bandit","Lupo mannaro",
                   "Vampiro","Troll","Ogre","Draghetto","Demone","Non-morto",
                   "Elementale","Golem","Licantropo","Cultista","Assassino"]
TIPI_NEMICO_EN = ["Goblin","Orc","Skeleton","Zombie","Bandit","Werewolf",
                   "Vampire","Troll","Ogre","Dragonling","Demon","Undead",
                   "Elemental","Golem","Lycanthrope","Cultist","Assassin"]


def _stat_casuale(base: int, varianza: int) -> int:
    return max(1, min(30, base + random.randint(-varianza, varianza)))


def genera_npc(lingua: str = "it") -> dict:
    """Genera una scheda NPC casuale."""
    rng = random
    sesso = rng.choice(["m", "f"])
    razze_list = RAZZE_IT if lingua == "it" else RAZZE_EN
    razza = rng.choice(razze_list)
    razza_key = razza.lower()

    # Mappa razza → chiave nomi
    chiave_nomi = "umano_m"
    if "elfo" in razza_key or "elf" in razza_key:
        chiave_nomi = f"elfo_{sesso}"
    elif "nano" in razza_key or "dwarf" in razza_key:
        chiave_nomi = f"nano_{sesso}"
    elif "halfling" in razza_key:
        chiave_nomi = f"halfling_{sesso}"
    else:
        chiave_nomi = f"umano_{sesso}"

    nomi_dict  = NOMI_IT if lingua == "it" else NOMI_EN
    cognomi    = COGNOMI_IT if lingua == "it" else COGNOMI_EN
    classi     = CLASSI_NPC_IT if lingua == "it" else CLASSI_NPC_EN

    nome = (rng.choice(nomi_dict.get(chiave_nomi, nomi_dict["umano_m"]))
            + " " + rng.choice(cognomi))
    classe = rng.choice(classi)

    pf = rng.randint(6, 20)
    return {
        "tipo":    "npc",
        "nome":    nome,
        "razza":   razza,
        "classe":  classe,
        "pf":      pf,
        "pf_max":  pf,
        "ca":      rng.randint(10, 14),
        "statistiche": {
            "for": _stat_casuale(10, 4),
            "des": _stat_casuale(10, 4),
            "cos": _stat_casuale(10, 4),
            "int": _stat_casuale(10, 4),
            "sag": _stat_casuale(10, 4),
            "car": _stat_casuale(10, 4),
        },
        "colore":  (rng.randint(80,200), rng.randint(80,200), rng.randint(80,200)),
    }


def genera_nemico(lingua: str = "it", difficolta: str = "medio") -> dict:
    """Genera una scheda Nemico casuale."""
    rng = random
    tipi   = TIPI_NEMICO_IT if lingua == "it" else TIPI_NEMICO_EN
    tipo   = rng.choice(tipi)
    nomi   = NOMI_IT if lingua == "it" else NOMI_EN
    chiave = "mostro"
    nome   = rng.choice(nomi[chiave]) + " " + rng.choice(
        ["il Terribile","il Maledetto","delle Ombre","Sanguinario",
         "the Terrible","the Cursed","of Shadows","Bloodthirsty"]
        if lingua == "it" else
        ["the Terrible","the Cursed","of Shadows","Bloodthirsty",
         "the Ancient","the Vile","Doombringer","the Cruel"])

    moltiplicatori = {"facile": 0.6, "medio": 1.0, "difficile": 1.6, "boss": 2.5}
    m = moltiplicatori.get(difficolta, 1.0)

    pf = int(rng.randint(15, 50) * m)
    return {
        "tipo":    "nemico",
        "nome":    nome,
        "razza":   tipo,
        "classe":  tipo,
        "difficolta": difficolta,
        "pf":      pf,
        "pf_max":  pf,
        "ca":      int(rng.randint(11, 18) * min(m, 1.3)),
        "statistiche": {
            "for": _stat_casuale(int(12 * m), 3),
            "des": _stat_casuale(int(10 * m), 3),
            "cos": _stat_casuale(int(12 * m), 3),
            "int": _stat_casuale(6,  3),
            "sag": _stat_casuale(8,  3),
            "car": _stat_casuale(6,  3),
        },
        "colore": (rng.randint(150,220), rng.randint(30,80), rng.randint(30,80)),
    }


def genera_nome(razza: str = "umano", sesso: str = "m",
                lingua: str = "it") -> str:
    """Genera solo un nome casuale."""
    nomi  = NOMI_IT if lingua == "it" else NOMI_EN
    cog   = COGNOMI_IT if lingua == "it" else COGNOMI_EN
    chiave = f"{razza.lower()}_{sesso}"
    if chiave not in nomi:
        chiave = f"umano_{sesso}"
    return random.choice(nomi[chiave]) + " " + random.choice(cog)
