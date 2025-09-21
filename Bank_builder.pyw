#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
import importlib

# --- ttkbootstrap (thème moderne + dark mode) ---
from ttkbootstrap import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ---------- Utils chemins (compatibles PyInstaller) ----------
def resource_path(relpath: str | Path) -> Path:
    """Chemin réel d'une ressource embarquée (--add-data) ou locale."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relpath

def app_dir() -> Path:
    """Dossier de l'exe si gelé, sinon dossier du script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

APP_DIR = app_dir()

# ---------- Config ----------
BANK_FILENAME = "bank.yaml"
BANK_PATH = APP_DIR / BANK_FILENAME  # bank.yaml à côté de l'exe
STATE_FLAGS_DEFAULT = 1
LANG_FILES = {"fr": "fr.json", "en": "en.json"}
DEFAULT_LANG = "fr"

# ----- (Optionnel) Kill switch du décodeur externe -----
DISABLE_DECODER = False

# ----- Intégration du décodeur externe (main.py) avec reload -----
ext_decoder = None
has_external_decoder = False

def load_decoder():
    """Charge/recharge main.py et expose has_external_decoder (désactivable)."""
    global ext_decoder, has_external_decoder
    if DISABLE_DECODER:
        ext_decoder = None
        has_external_decoder = False
        return None
    try:
        if ext_decoder is None:
            ext_decoder = importlib.import_module("main")   # main.py à côté (ou embarqué)
        else:
            importlib.reload(ext_decoder)                   # hot-reload
        has_external_decoder = hasattr(ext_decoder, "decode_item_serial")
    except Exception:
        ext_decoder = None
        has_external_decoder = False
    return ext_decoder

# map des catégories (clé en minuscules) -> libellés UI
DECODER_CAT_MAP = {
    "weapon": "Weapons",
    "equipment": "Equipment",
    "equipment_alt": "Equipment Alt",
    "weapon_special": "Special Items",
    "special": "Special Items",
    "utility": "Unknown",
    "consumable": "Unknown",
    "decode_failed": "Unknown",
    "unknown": "Unknown",
}

# --------- i18n ----------
class I18N:
    def __init__(self, lang="fr"):
        self.lang = lang
        self.data = {}
        self._load(lang)

    def _load(self, lang: str):
        fname = LANG_FILES.get(lang, LANG_FILES[DEFAULT_LANG])
        path = resource_path(fname)
        try:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # fallback minimal si JSON manquant
            self.data = {
                "app_title": "Bank Format YAML Builder by F3F364fr and GPT5",
                "ok": "OK", "warn": "Warning", "err": "Error", "info": "Info",
                "copy_serials": "Copy serial(s)",
                "selected_one": "Selected: {serial}",
                "selected_many": "{n} selected",
                "selected_none": "No selection",
                "all": "All",
                "decrypt_btn": "Decrypt selection (fill comments)",
                "decrypt_done": "Decrypt finished: {n} item(s) enriched.",
                "auto_decode_on_add": "Auto: fill comment via decoder on add",
                "serial_col": "Serial", "category_col": "Category", "comment_col": "Comment",
                "category": "Category", "search_contains": "Search (contains)",
                "filter": "Filter", "reset": "Reset", "dedupe": "Deduplicate (by serial)",
                "delete_selected": "Delete selected",
                "comment_apply_label": "Comment → apply to selected items",
                "comment_apply_btn": "Add/Replace comment on selection",
                "state_flags_default": "state_flags default:",
                "indent_slot": "Slot indent (spaces):",
                "indent_inner": "Inner indent:",
                "merge_btn": "Merge → bank.yaml",
                "export_btn": "Export…",
                "paste_hint": "Paste @U… lines or YAML blocks (serial: '...'), then “Add to list”.",
                "add_to_list": "Add → List", "clear_box": "Clear box", "import_txt": "Import .txt…",
                "added_n": "{n} serial(s) added.", "no_serial_detected": "No serial detected",
                "paste_examples": "Paste either @U... lines or YAML blocks with 'serial: ...'.",
                "cant_read_file": "Cannot read file:", "nothing_to_export": "The view is empty.",
                "export_title": "Export YAML", "export_written": "File written:",
                "write_failed": "Write failed:", "merge_done": "Bank:", "merge_new_added": "New added:",
                "dedupe_removed": "Duplicates removed: {removed}\nUnique total: {total}",
                "no_selection": "Select at least one row.",
                "with_comment": "With comment",
                "without_comment": "Without comment",
                "lang_fr": "FR", "lang_en": "EN"
            }

    def set_lang(self, lang: str):
        self.lang = lang
        self._load(lang)

    def t(self, key: str, **kwargs):
        val = self.data.get(key, key)
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

i18n = I18N(DEFAULT_LANG)

# --------- Fonctions utilitaires ---------
def detect_category(serial: str) -> str:
    if serial.startswith("@Ugr"):
        return "Weapons"
    if serial.startswith("@Uge"):
        return "Equipment"
    if serial.startswith("@Ugd"):
        return "Equipment Alt"
    if serial.startswith("@Ugw") or serial.startswith("@Ugu") or serial.startswith("@Ugf") or serial.startswith("@Ug!"):
        return "Special Items"
    return "Unknown"

def escape_yaml_single_quoted(val: str) -> str:
    return val.replace("'", "''")

def parse_bank_yaml_simple(path: Path):
    """
    Parse simple du format:
    slot_X:
      serial: '...'
      state_flags: N
    Supporte commentaire inline après serial: serial: '...' # xxx
    """
    entries = {}
    existing_serials = set()
    max_slot = -1
    if not path.exists():
        return entries, -1, existing_serials
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return entries, -1, existing_serials

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        m_slot = re.match(r"\s*slot_(\d+)\s*:\s*$", line)
        if m_slot:
            idx = int(m_slot.group(1))
            ser = None
            sf = STATE_FLAGS_DEFAULT
            comment = ""
            j = i + 1
            while j < len(lines):
                l2 = lines[j].rstrip()
                if re.match(r"\s*slot_(\d+)\s*:\s*$", l2):
                    break
                m_ser = re.match(r"\s*serial\s*:\s*(.+?)\s*$", l2)
                if m_ser and ser is None:
                    val = m_ser.group(1)
                    mq = re.match(r"""['"](.*)['"]\s*(#\s*(.*))?$""", val)
                    if mq:
                        ser = mq.group(1)
                        if mq.group(3):
                            comment = mq.group(3).strip()
                    else:
                        if " #" in val:
                            ser, c = val.split(" #", 1)
                            ser = ser.strip()
                            comment = c.strip()
                        else:
                            ser = val.strip()
                m_sf = re.match(r"\s*state_flags\s*:\s*(\d+)\s*$", l2)
                if m_sf:
                    sf = int(m_sf.group(1))
                j += 1
            if ser is not None:
                entries[idx] = {"serial": ser, "state_flags": sf, "comment": comment}
                existing_serials.add(ser)
                if idx > max_slot:
                    max_slot = idx
            i = j
        else:
            i += 1
    return entries, max_slot, existing_serials

def write_yaml_manual(path: Path, ordered_items, state_flags=STATE_FLAGS_DEFAULT, with_comments=True,
                      slot_indent=0, inner_indent=2):
    """
    ordered_items: liste d'objets {"serial","comment","category"}
    slot_indent: nb d'espaces avant 'slot_X:'
    inner_indent: nb d'espaces supplémentaires pour 'serial' et 'state_flags'
    """
    s = " " * max(0, int(slot_indent))
    i = " " * max(0, int(slot_indent) + int(inner_indent))
    lines = []
    for idx, it in enumerate(ordered_items):
        serial_val = it["serial"]
        comment = (it.get("comment") or "").strip()
        lines.append(f"{s}slot_{idx}:")
        if with_comments and comment:
            lines.append(f"{i}serial: '{escape_yaml_single_quoted(serial_val)}' # {comment}")
        else:
            lines.append(f"{i}serial: '{escape_yaml_single_quoted(serial_val)}'")
        lines.append(f"{i}state_flags: {int(state_flags)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def extract_serials(blob: str):
    """
    Extrait serials depuis:
    - blocs YAML: serial: '...'/ "..." / non-quoted
    - lignes brutes: @U....
    """
    serials = []
    seen = set()

    re_yaml_serial = re.compile(r"""serial\s*:\s*(?:'([^']*)'|"([^"]*)"|([^\s#]+))""", re.IGNORECASE)
    for m in re_yaml_serial.finditer(blob):
        val = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if val and val not in seen:
            serials.append(val)
            seen.add(val)

    for line in blob.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].strip()
        if re.match(r"^@U\S+$", line) and line not in seen:
            serials.append(line)
            seen.add(line)
    return serials

def try_decode_and_enrich(item: dict) -> bool:
    """
    Essaye main.decode_item_serial(serial):
      - si weapon_name et commentaire vide -> commentaire
      - si item_category -> catégorie (mappée)
    """
    mod = load_decoder()
    if not (mod and hasattr(mod, "decode_item_serial")):
        return False

    serial = item.get("serial", "")
    if not serial:
        return False

    try:
        decoded = mod.decode_item_serial(serial)
    except Exception:
        return False
    if not decoded:
        return False

    changed = False

    wn = getattr(decoded, "weapon_name", None)
    if wn and not (item.get("comment") or "").strip():
        item["comment"] = str(wn).strip()
        changed = True

    dec_cat = getattr(decoded, "item_category", None)
    if isinstance(dec_cat, str) and dec_cat.strip():
        key = dec_cat.strip().lower()
        mapped = DECODER_CAT_MAP.get(key, "Unknown")
        if item.get("category") != mapped:
            item["category"] = mapped
            changed = True

    return changed

# --------- App (ttkbootstrap Window) ---------
class App(tb.Window):
    def __init__(self):
        # Thème par défaut (sombre). Met "flatly" si tu préfères clair.
        super().__init__(themename="darkly")
        self.title("Bank Format YAML Builder by F3F364fr and GPT5")
        self.geometry("1000x600")
        self.minsize(1000, 600)

        # Thème auto selon l'heure (optionnel)
        try:
            import datetime as _dt
            hour = _dt.datetime.now().hour
            if 7 <= hour < 20:
                self.switch_theme("flatly")   # clair le jour
            else:
                self.switch_theme("darkly")   # sombre le soir
        except Exception:
            pass

        load_decoder()

        # Banque existante
        self.bank_entries, self.bank_max_slot, self.bank_serials = parse_bank_yaml_simple(BANK_PATH)

        # Items (source)
        self.items = []
        for idx in sorted(self.bank_entries.keys()):
            ser = self.bank_entries[idx]["serial"]
            com = self.bank_entries[idx].get("comment", "")
            self.items.append({"serial": ser, "comment": com, "category": detect_category(ser)})

        # Vue
        self.view_items = list(self.items)

        # --- Barre langue + Thème ---
        langbar = ttk.Frame(self)
        langbar.pack(fill="x", padx=10, pady=(8,0))
        self.btn_fr = ttk.Button(langbar, text=i18n.t("lang_fr"), width=4, command=lambda: self.switch_lang("fr"))
        self.btn_en = ttk.Button(langbar, text=i18n.t("lang_en"), width=4, command=lambda: self.switch_lang("en"))
        self.btn_fr.pack(side="right")
        self.btn_en.pack(side="right", padx=6)

        themebar = ttk.Frame(langbar)
        themebar.pack(side="left")
        ttk.Button(themebar, text="Light", command=lambda: self.switch_theme("flatly")).pack(side="left", padx=(0,6))
        ttk.Button(themebar, text="Dark", command=lambda: self.switch_theme("darkly")).pack(side="left")

        # --- Zone de collage ---
        frm_top = ttk.Frame(self)
        frm_top.pack(fill="x", padx=10, pady=(8,6))
        self.lbl_paste = ttk.Label(frm_top, text=i18n.t("paste_hint"))
        self.lbl_paste.pack(anchor="w")
        self.txt_input = tk.Text(frm_top, height=5)   # Tk Text (on gère ses couleurs à part)
        self.txt_input.pack(fill="x", pady=4)

        bar = ttk.Frame(frm_top)
        bar.pack(fill="x")
        self.btn_add = ttk.Button(bar, text=i18n.t("add_to_list"), command=self.add_from_text)
        self.btn_add.pack(side="left")
        self.btn_clear = ttk.Button(bar, text=i18n.t("clear_box"), command=lambda: self.txt_input.delete("1.0","end"))
        self.btn_clear.pack(side="left", padx=6)
        self.btn_import = ttk.Button(bar, text=i18n.t("import_txt"), command=self.import_txt)
        self.btn_import.pack(side="left", padx=6)

        # --- Filtres / actions ---
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=10, pady=(0,6))

        self.lbl_cat = ttk.Label(ctrl, text=i18n.t("category") + ":")
        self.lbl_cat.pack(side="left")
        self.var_cat = tk.StringVar(value=i18n.t("all"))
        all_label = i18n.t("all")
        cats_localized = [
            all_label,
            "Weapons", "Equipment", "Equipment Alt", "Special Items", "Unknown",
            i18n.t("with_comment"), i18n.t("without_comment")
        ]
        self.cb_cat = ttk.Combobox(ctrl, values=cats_localized, textvariable=self.var_cat, state="readonly", width=22)
        self.cb_cat.pack(side="left", padx=6)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        self.lbl_search = ttk.Label(ctrl, text=i18n.t("search_contains") + ":")
        self.lbl_search.pack(side="left", padx=(12,0))
        self.var_query = tk.StringVar()
        ent = ttk.Entry(ctrl, textvariable=self.var_query, width=28)
        ent.pack(side="left", padx=6)
        self.btn_filter = ttk.Button(ctrl, text=i18n.t("filter"), command=self.apply_filters)
        self.btn_filter.pack(side="left")
        self.btn_reset = ttk.Button(ctrl, text=i18n.t("reset"), command=self.reset_filters)
        self.btn_reset.pack(side="left", padx=6)

        self.btn_dedupe = ttk.Button(ctrl, text=i18n.t("dedupe"), command=self.deduplicate_items)
        self.btn_dedupe.pack(side="right")
        self.btn_delete = ttk.Button(ctrl, text=i18n.t("delete_selected"), command=self.remove_selected)
        self.btn_delete.pack(side="right", padx=6)

        # --- Table (Treeview + scrollbar) ---
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.tree = ttk.Treeview(
            table_frame,
            columns=("serial","category","comment"),
            show="headings",
            selectmode="extended"
        )
        self.tree.heading("serial", text=i18n.t("serial_col"), command=lambda: self.sort_by("serial"))
        self.tree.heading("category", text=i18n.t("category_col"), command=lambda: self.sort_by("category"))
        self.tree.heading("comment", text=i18n.t("comment_col"), command=lambda: self.sort_by("comment"))
        self.tree.column("serial", width=500, anchor="w")
        self.tree.column("category", width=200, anchor="w")
        self.tree.column("comment", width=300, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        # Molette souris
        def _on_tree_mousewheel(event):
            if getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            else:
                delta = -1 * (event.delta // 120 if event.delta else 0)
            self.tree.yview_scroll(delta, "units")
            return "break"
        self.tree.bind("<MouseWheel>", _on_tree_mousewheel)
        self.tree.bind("<Button-4>", _on_tree_mousewheel)
        self.tree.bind("<Button-5>", _on_tree_mousewheel)

        # --- Menu contextuel & raccourcis (copie serial) ---
        self.tree_menu = tk.Menu(self, tearoff=0)
        self.tree_menu.add_command(label=i18n.t("copy_serials"), command=self.copy_selected_serials)
        self.tree.bind("<Button-3>", self._show_tree_context_menu)
        self.tree.bind("<Button-2>", self._show_tree_context_menu)
        self.tree.bind("<Control-c>", self.copy_selected_serials)
        self.tree.bind("<Command-c>", self.copy_selected_serials)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # --- Zone commentaire ---
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0,10))

        hdr = ttk.Frame(bottom)
        hdr.pack(fill="x")
        self.lbl_comment = ttk.Label(hdr, text=i18n.t("comment_apply_label"))
        self.lbl_comment.pack(side="left", anchor="w")

        self.var_selected_info = tk.StringVar(value=i18n.t("selected_none"))
        self.lbl_selected_info = ttk.Label(hdr, textvariable=self.var_selected_info)
        self.lbl_selected_info.pack(side="right", anchor="e")

        # Champ commentaire
        self.entry_comment = ttk.Entry(bottom)
        self.entry_comment.pack(fill="x", pady=(4,0))

        # Ligne unique : Ajouter/Remplacer + Auto + Décrypter
        comment_bar = ttk.Frame(bottom)
        comment_bar.pack(fill="x", pady=(6,0))

        self.btn_apply_comment = ttk.Button(
            comment_bar,
            text=i18n.t("comment_apply_btn"),
            command=self.add_comment_to_selected
        )
        self.btn_apply_comment.pack(side="left")

        # (déplacés depuis action_bar)
        self.var_auto_decode = tk.BooleanVar(value=True)
        self.chk_auto_decode = ttk.Checkbutton(
            comment_bar,
            text=i18n.t("auto_decode_on_add"),
            variable=self.var_auto_decode,
            onvalue=True, offvalue=False
        )
        self.chk_auto_decode.pack(side="left", padx=12)

        self.btn_dec_sel = ttk.Button(
            comment_bar,
            text=i18n.t("decrypt_btn"),
            command=self.decrypt_selection_fill_comments
        )
        self.btn_dec_sel.pack(side="left", padx=12)

        # Désactiver si pas de décodeur
        if not has_external_decoder:
            self.btn_dec_sel.config(state="disabled")
            self.chk_auto_decode.config(state="disabled")

        # --- Options + actions (sans Auto/Décrypter désormais) ---
        action_bar = ttk.Frame(self)
        action_bar.pack(fill="x", padx=10, pady=(0,12))

        self.var_sf = tk.IntVar(value=STATE_FLAGS_DEFAULT)
        self.lbl_sf = ttk.Label(action_bar, text=i18n.t("state_flags_default"))
        self.lbl_sf.pack(side="left")
        self.spin_sf = ttk.Spinbox(action_bar, from_=0, to=2_147_483_647, textvariable=self.var_sf, width=10)
        self.spin_sf.pack(side="left", padx=6)

        self.var_slot_indent = tk.IntVar(value=0)
        self.var_inner_indent = tk.IntVar(value=2)
        self.lbl_slot_indent = ttk.Label(action_bar, text=i18n.t("indent_slot"))
        self.lbl_slot_indent.pack(side="left", padx=(18,0))
        self.spin_slot_indent = ttk.Spinbox(action_bar, from_=0, to=64, textvariable=self.var_slot_indent, width=5)
        self.spin_slot_indent.pack(side="left", padx=6)
        self.lbl_inner_indent = ttk.Label(action_bar, text=i18n.t("indent_inner"))
        self.lbl_inner_indent.pack(side="left")
        self.spin_inner_indent = ttk.Spinbox(action_bar, from_=0, to=16, textvariable=self.var_inner_indent, width=5)
        self.spin_inner_indent.pack(side="left", padx=6)

        self.btn_merge = ttk.Button(action_bar, text=i18n.t("merge_btn"), command=self.merge_to_bank)
        self.btn_merge.pack(side="right")
        self.btn_export = ttk.Button(action_bar, text=i18n.t("export_btn"), command=self.export_to_file)
        self.btn_export.pack(side="right", padx=8)

        self.sort_state = {"serial": True, "category": True, "comment": True}

        # Initialiser thème pour Text et remplir la table
        self._apply_text_theme()
        self.refresh_tree()
        self.update_title()

    # ---------- Thème ----------
    def switch_theme(self, name: str):
        try:
            self.style.theme_use(name)
        except Exception:
            tb.Style().theme_use(name)
        self._apply_text_theme()

    def _apply_text_theme(self):
        try:
            colors = self.style.colors
            theme_name = self.style.theme.name
        except Exception:
            colors = tb.Style().colors
            theme_name = "darkly"
        is_dark = theme_name in {"darkly","cyborg","superhero","solar","vapor"}
        if is_dark:
            bg = colors.dark
            fg = colors.light
        else:
            bg = "white"
            fg = "black"
        try:
            self.txt_input.configure(bg=bg, fg=fg, insertbackground=fg)
        except Exception:
            pass

    # ---------- Mise à jour du titre ----------
    def update_title(self):
        count = len(self.items)
        self.title(f"Bank Format YAML Builder by F3F364fr and GPT5 — {count} serials")

    # ---------- i18n refresh ----------
    def switch_lang(self, lang):
        i18n.set_lang(lang)
        # self.title(i18n.t("app_title"))  # on garde le compteur plutôt
        self.lbl_paste.config(text=i18n.t("paste_hint"))
        self.btn_add.config(text=i18n.t("add_to_list"))
        self.btn_clear.config(text=i18n.t("clear_box"))
        self.btn_import.config(text=i18n.t("import_txt"))
        self.lbl_cat.config(text=i18n.t("category") + ":")
        current = self.var_cat.get()
        all_label = i18n.t("all")
        cats_localized = [
            all_label,
            "Weapons", "Equipment", "Equipment Alt", "Special Items", "Unknown",
            i18n.t("with_comment"), i18n.t("without_comment")
        ]
        self.cb_cat.config(values=cats_localized)
        if current.lower() in ("all","tous"):
            self.var_cat.set(all_label)
        else:
            self.var_cat.set(current)
        self.lbl_search.config(text=i18n.t("search_contains") + ":")
        self.btn_filter.config(text=i18n.t("filter"))
        self.btn_reset.config(text=i18n.t("reset"))
        self.btn_dedupe.config(text=i18n.t("dedupe"))
        self.btn_delete.config(text=i18n.t("delete_selected"))
        self.tree.heading("serial", text=i18n.t("serial_col"))
        self.tree.heading("category", text=i18n.t("category_col"))
        self.tree.heading("comment", text=i18n.t("comment_col"))
        self.lbl_comment.config(text=i18n.t("comment_apply_label"))
        self.btn_apply_comment.config(text=i18n.t("comment_apply_btn"))
        self.lbl_sf.config(text=i18n.t("state_flags_default"))
        self.lbl_slot_indent.config(text=i18n.t("indent_slot"))
        self.lbl_inner_indent.config(text=i18n.t("indent_inner"))
        self.btn_merge.config(text=i18n.t("merge_btn"))
        self.btn_export.config(text=i18n.t("export_btn"))
        self.chk_auto_decode.config(text=i18n.t("auto_decode_on_add"))
        self.btn_dec_sel.config(text=i18n.t("decrypt_btn"))
        try:
            self.tree_menu.entryconfig(0, label=i18n.t("copy_serials"))
        except Exception:
            pass
        sel = self.tree.selection()
        if not sel:
            self.var_selected_info.set(i18n.t("selected_none"))
        elif len(sel) == 1:
            vals = self.tree.item(sel[0], "values")
            self.var_selected_info.set(i18n.t("selected_one", serial=vals[0]))
        else:
            self.var_selected_info.set(i18n.t("selected_many", n=len(sel)))
        self.update_title()

    # ---------- Model <-> View ----------
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for it in self.view_items:
            self.tree.insert("", "end", values=(it["serial"], it["category"], it.get("comment","")))

    def apply_filters(self):
        cat_label = self.var_cat.get()
        if cat_label.lower() in ("tous",):
            cat = "All"
        elif cat_label.lower() in ("all",):
            cat = "All"
        else:
            cat = cat_label

        q = self.var_query.get().strip().lower()
        base = list(self.items)

        if cat and cat != "All":
            if cat in (i18n.t("with_comment"),):
                base = [it for it in base if (it.get("comment") or "").strip()]
            elif cat in (i18n.t("without_comment"),):
                base = [it for it in base if not (it.get("comment") or "").strip()]
            else:
                base = [it for it in base if it["category"] == cat]

        if q:
            base = [it for it in base if (q in it["serial"].lower() or q in (it.get("comment","").lower()))]

        self.view_items = base
        self.refresh_tree()
        # self.update_title()  # active si tu veux compter la vue plutôt que la base

    def reset_filters(self):
        self.var_cat.set(i18n.t("all"))
        self.var_query.set("")
        self.view_items = list(self.items)
        self.refresh_tree()

    def sort_by(self, key):
        reverse = not self.sort_state.get(key, True)
        self.view_items.sort(key=lambda it: (it.get(key) or "").lower(), reverse=reverse)
        self.sort_state[key] = reverse
        self.refresh_tree()

    def selected_indices_in_view(self):
        sel = []
        for iid in self.tree.selection():
            vals = self.tree.item(iid, "values")
            for idx, it in enumerate(self.view_items):
                if (it["serial"], it["category"], it.get("comment","")) == (vals[0], vals[1], vals[2]):
                    sel.append(idx)
                    break
        return sorted(set(sel), reverse=True)

    # ---------- Copie serials ----------
    def copy_selected_serials(self, event=None):
        serials = []
        for iid in self.tree.selection():
            vals = self.tree.item(iid, "values")
            if vals:
                serials.append(vals[0])
        if not serials:
            return
        text = "\n".join(serials)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            pass
        messagebox.showinfo(i18n.t("ok"), i18n.t("copy_serials"))

    def _tree_focus_row_under_mouse(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
                self.tree.focus(row_id)
            self.on_tree_select(None)
            return True
        return False

    def _show_tree_context_menu(self, event):
        self._tree_focus_row_under_mouse(event)
        try:
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tree_menu.grab_release()

    # ---------- Sélection : pré-remplir commentaire + label ----------
    def on_tree_select(self, event=None):
        sel_iids = self.tree.selection()
        if not sel_iids:
            self.var_selected_info.set(i18n.t("selected_none"))
            return

        rows = [self.tree.item(iid, "values") for iid in sel_iids]
        serials = [r[0] for r in rows]
        comments = [r[2] for r in rows]

        if len(rows) == 1:
            self.var_selected_info.set(i18n.t("selected_one", serial=serials[0]))
            self.entry_comment.delete(0, "end")
            if comments[0]:
                self.entry_comment.insert(0, comments[0])
        else:
            self.var_selected_info.set(i18n.t("selected_many", n=len(rows)))
            unique_comments = { (c or "").strip() for c in comments }
            self.entry_comment.delete(0, "end")
            if len(unique_comments) == 1:
                only = unique_comments.pop()
                if only:
                    self.entry_comment.insert(0, only)

    # ---------- Actions ----------
    def add_from_text(self):
        raw = self.txt_input.get("1.0", "end")
        serials = extract_serials(raw)
        if not serials:
            messagebox.showwarning(i18n.t("warn"), i18n.t("no_serial_detected") + "\n" + i18n.t("paste_examples"))
            return

        auto = True if hasattr(self, "var_auto_decode") and self.var_auto_decode.get() else False
        enriched = 0

        for code in serials:
            it = {"serial": code, "comment": "", "category": detect_category(code)}
            if auto:
                if try_decode_and_enrich(it):
                    enriched += 1
            self.items.append(it)

        self.apply_filters()
        self.update_title()
        msg = i18n.t("added_n", n=len(serials))
        if enriched:
            msg += "\n" + i18n.t("decrypt_done", n=enriched)
        messagebox.showinfo(i18n.t("ok"), msg)

    def import_txt(self):
        path = filedialog.askopenfilename(title=i18n.t("import_txt"),
                                          filetypes=[("Text","*.txt"),("All files","*.*")])
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            messagebox.showerror(i18n.t("err"), f"{i18n.t('cant_read_file')} {e}")
            return
        self.txt_input.delete("1.0","end")
        self.txt_input.insert("1.0", content)

    def remove_selected(self):
        idxs_in_view = self.selected_indices_in_view()
        if not idxs_in_view:
            return
        to_remove = [self.view_items[i] for i in idxs_in_view]
        new_items = []
        for it in self.items:
            if it not in to_remove:
                new_items.append(it)
        self.items = new_items
        self.apply_filters()
        self.update_title()

    def add_comment_to_selected(self):
        comment = self.entry_comment.get().strip()
        idxs_in_view = self.selected_indices_in_view()
        if not idxs_in_view:
            messagebox.showwarning(i18n.t("warn"), i18n.t("no_selection"))
            return
        for i in idxs_in_view:
            self.view_items[i]["comment"] = comment
        self.refresh_tree()
        messagebox.showinfo(i18n.t("ok"), i18n.t("comment_apply_btn"))

    def decrypt_selection_fill_comments(self):
        sel_idxs = self.selected_indices_in_view()
        if not sel_idxs:
            return
        enriched = 0
        for i in sel_idxs:
            it = self.view_items[i]
            if try_decode_and_enrich(it):
                enriched += 1
        self.refresh_tree()
        messagebox.showinfo(i18n.t("info"), i18n.t("decrypt_done", n=enriched))

    def deduplicate_items(self):
        """
        Règles:
        - Clé = serial
        - Deux avec commentaire -> garder le premier rencontré
        - Avec commentaire vs sans -> garder celui AVEC commentaire
        """
        seen = {}
        removed = 0
        result = []
        for it in self.items:
            ser = it["serial"]
            if ser not in seen:
                seen[ser] = it
                result.append(it)
            else:
                kept = seen[ser]
                has_comment_kept = bool((kept.get("comment") or "").strip())
                has_comment_new = bool((it.get("comment") or "").strip())
                if has_comment_new and not has_comment_kept:
                    idx = result.index(kept)
                    result[idx] = it
                    seen[ser] = it
                    removed += 1
                else:
                    removed += 1
        self.items = result
        self.apply_filters()
        self.update_title()
        messagebox.showinfo(i18n.t("info"), i18n.t("dedupe_removed", removed=removed, total=len(self.items)))

    # ---------- Export / Merge ----------
    def current_view_for_export(self):
        return list(self.view_items)

    def export_to_file(self):
        data = self.current_view_for_export()
        if not data:
            messagebox.showwarning(i18n.t("warn"), i18n.t("nothing_to_export"))
            return
        path_str = filedialog.asksaveasfilename(
            title=i18n.t("export_title"),
            defaultextension=".yaml",
            initialfile="export.yaml",
            filetypes=[("YAML","*.yaml"),("All files","*.*")]
        )
        if not path_str:
            return
        try:
            write_yaml_manual(
                Path(path_str),
                data,
                state_flags=self.var_sf.get(),
                with_comments=True,
                slot_indent=self.var_slot_indent.get(),
                inner_indent=self.var_inner_indent.get(),
            )
        except Exception as e:
            messagebox.showerror(i18n.t("err"), f"{i18n.t('write_failed')} {e}")
            return
        messagebox.showinfo(i18n.t("ok"), f"{i18n.t('export_written')} {path_str}")

    def merge_to_bank(self):
        existing_entries, max_slot, existing_serials = parse_bank_yaml_simple(BANK_PATH)

        merged_items = []
        for idx in sorted(existing_entries.keys()):
            ser = existing_entries[idx]["serial"]
            com = existing_entries[idx].get("comment", "")
            merged_items.append({"serial": ser, "comment": com, "category": detect_category(ser)})

        new_added = 0
        for it in self.items:
            ser = it["serial"]
            if ser in existing_serials:
                continue  # commentaire seul ne modifie pas l'existant
            merged_items.append({"serial": ser, "comment": (it.get("comment") or ""), "category": detect_category(ser)})
            existing_serials.add(ser)
            new_added += 1

        try:
            write_yaml_manual(
                BANK_PATH,
                merged_items,
                state_flags=self.var_sf.get(),
                with_comments=True,
                slot_indent=self.var_slot_indent.get(),
                inner_indent=self.var_inner_indent.get(),
            )
        except Exception as e:
            messagebox.showerror(i18n.t("err"), f"{i18n.t('write_failed')} {e}")
            return

        messagebox.showinfo(i18n.t("ok"), f"{i18n.t('merge_done')} {BANK_PATH}\n{i18n.t('merge_new_added')} {new_added}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
