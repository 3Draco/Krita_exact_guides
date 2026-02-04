from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QLocale
import json
import os

class ExactGuidesDocker(DockWidget):
    def __init__(self):
        super().__init__()
        
        current_lang = QLocale().name()[:2].lower()
        self.texts = self.get_strings(current_lang)
        
        self.setWindowTitle(self.texts["title"])
        self._block_signals = False
        self.custom_names = {} 
        self.version = "1.0"
        self.unit = "px" 

        self.save_path = os.path.join(os.path.expanduser("~"), ".krita_guides_layouts.json")
        self.saved_layouts = self.load_from_disk()
        
        # --- UI STRUKTUR MIT SYMMETRISCHEM ABSTAND ---
        outer_widget = QWidget()
        self.setWidget(outer_widget)
        
        h_box = QHBoxLayout(outer_widget)
        h_box.setContentsMargins(0, 5, 0, 5)
        h_box.addSpacing(15) 

        content_widget = QWidget()
        h_box.addWidget(content_widget)
        h_box.addSpacing(15) 

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        
        # --- Ansicht-Optionen (Checkboxen) ---
        settings_layout = QGridLayout()
        self.cb_show_guides = QCheckBox(self.texts["show_guides"])
        self.cb_show_guides.toggled.connect(lambda: self.set_krita_state("view_show_guides", self.cb_show_guides))
        settings_layout.addWidget(self.cb_show_guides, 0, 0)

        self.cb_show_rulers = QCheckBox(self.texts["show_rulers"])
        self.cb_show_rulers.toggled.connect(lambda: self.set_krita_state("view_ruler", self.cb_show_rulers))
        settings_layout.addWidget(self.cb_show_rulers, 0, 1)

        self.cb_lock_guides = QCheckBox(self.texts["lock_guides"])
        self.cb_lock_guides.toggled.connect(lambda: self.set_krita_state("view_lock_guides", self.cb_lock_guides))
        settings_layout.addWidget(self.cb_lock_guides, 1, 0)

        self.cb_snap_guides = QCheckBox(self.texts["snap_guides"])
        self.cb_snap_guides.toggled.connect(lambda: self.set_krita_state("view_snap_to_guides", self.cb_snap_guides))
        settings_layout.addWidget(self.cb_snap_guides, 1, 1)
        layout.addLayout(settings_layout)

        # --- Layout Management ---
        save_box = QGroupBox(self.texts["layouts"])
        save_layout = QVBoxLayout(save_box)
        self.layout_selector = QComboBox()
        self.update_combo_box()
        save_layout.addWidget(self.layout_selector)
        
        btn_row = QHBoxLayout()
        for btn_key, func in [("save", self.save_current_layout), ("load", self.load_selected_layout), ("delete", self.delete_selected_layout)]:
            btn = QPushButton(self.texts[btn_key])
            btn.clicked.connect(func)
            btn_row.addWidget(btn)
        save_layout.addLayout(btn_row)
        layout.addWidget(save_box)

        # --- Tabelle Header mit Einheiten-Wechsler ---
        table_header_layout = QHBoxLayout()
        table_label = QLabel(self.texts["table_label"])
        table_header_layout.addWidget(table_label)
        table_header_layout.addStretch()
        
        self.unit_selector = QComboBox()
        self.unit_selector.addItems(["px", "%"])
        self.unit_selector.currentTextChanged.connect(self.change_unit)
        table_header_layout.addWidget(self.unit_selector)
        layout.addLayout(table_header_layout)

        # --- Tabelle ---
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([self.texts["col_name"], self.texts["col_pos"]])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)
        
        # --- Untere Aktionen ---
        action_layout = QVBoxLayout()
        refresh_clear_layout = QHBoxLayout()
        btn_refresh = QPushButton(self.texts["refresh"])
        btn_refresh.clicked.connect(self.refresh_list)
        refresh_clear_layout.addWidget(btn_refresh)
        btn_clear = QPushButton(self.texts["clear_all"])
        btn_clear.setStyleSheet("background-color: #662222; color: #ddd;")
        btn_clear.clicked.connect(self.confirm_clear_all)
        refresh_clear_layout.addWidget(btn_clear)
        action_layout.addLayout(refresh_clear_layout)

        btn_split = QPushButton(self.texts["image_split"])
        btn_split.clicked.connect(lambda: self.trigger_action("imagesplit"))
        action_layout.addWidget(btn_split)
        layout.addLayout(action_layout)

        self.sync_checkboxes()

    def get_strings(self, lang):
        db = {
            "de": { "title": "Exact Guides", "show_guides": "Guides anzeigen", "show_rulers": "Lineale anzeigen", "lock_guides": "Guides sperren", "snap_guides": "Einrasten", "layouts": "Layouts", "save": "Speichern", "load": "Laden", "delete": "Löschen", "refresh": "Aktualisieren", "clear_all": "Alle löschen", "image_split": "Bild unterteilen...", "col_name": "Name", "col_pos": "Position", "confirm_del": "Löschen?", "confirm_clear": "Alle Guides löschen?", "table_label": "Hilfslinien:" },
            "en": { "title": "Exact Guides", "show_guides": "Show Guides", "show_rulers": "Show Rulers", "lock_guides": "Lock Guides", "snap_guides": "Snap", "layouts": "Saved Layouts", "save": "Save", "load": "Load", "delete": "Delete", "refresh": "Update", "clear_all": "Clear All", "image_split": "Image Split...", "col_name": "Name", "col_pos": "Position", "confirm_del": "Delete?", "confirm_clear": "Clear all?", "table_label": "Guides List:" },
            "fr": { "title": "Exact Guides", "show_guides": "Afficher les guides", "show_rulers": "Afficher les règles", "lock_guides": "Verrouiller les guides", "snap_guides": "Magnétisme", "layouts": "Dispositions", "save": "Enregistrer", "load": "Charger", "delete": "Supprimer", "refresh": "Actualiser", "clear_all": "Tout effacer", "image_split": "Diviser l'image...", "col_name": "Nom", "col_pos": "Position", "confirm_del": "Supprimer?", "confirm_clear": "Effacer tout?", "table_label": "Guides:" },
            "es": { "title": "Exact Guides", "show_guides": "Mostrar guías", "show_rulers": "Mostrar reglas", "lock_guides": "Bloquear guías", "snap_guides": "Ajustar", "layouts": "Diseños", "save": "Guardar", "load": "Cargar", "delete": "Eliminar", "refresh": "Actualizar", "clear_all": "Borrar todo", "image_split": "Dividir imagen...", "col_name": "Nombre", "col_pos": "Posición", "confirm_del": "¿Eliminar?", "confirm_clear": "¿Borrar todo?", "table_label": "Guías:" },
            "it": { "title": "Exact Guides", "show_guides": "Mostra guide", "show_rulers": "Mostra righelli", "lock_guides": "Blocca guide", "snap_guides": "Snap", "layouts": "Layout", "save": "Salva", "load": "Carica", "delete": "Elimina", "refresh": "Aggiorna", "clear_all": "Cancella tutto", "image_split": "Dividi immagine...", "col_name": "Nome", "col_pos": "Posizione", "confirm_del": "Elimina?", "confirm_clear": "Cancella tutto?", "table_label": "Guide:" },
            "ja": { "title": "Exact Guides", "show_guides": "ガイドを表示", "show_rulers": "定規を表示", "lock_guides": "ガイドをロック", "snap_guides": "スナップ", "layouts": "レイアウト", "save": "保存", "load": "読み込み", "delete": "削除", "refresh": "更新", "clear_all": "すべて消去", "image_split": "画像を分割...", "col_name": "名前", "col_pos": "位置", "confirm_del": "削除?", "confirm_clear": "消去しますか?", "table_label": "ガイドリスト:" },
            "zh": { "title": "Exact Guides", "show_guides": "显示辅助线", "show_rulers": "显示标尺", "lock_guides": "锁定辅助线", "snap_guides": "对齐", "layouts": "已保存布局", "save": "保存", "load": "加载", "delete": "删除", "refresh": "刷新", "clear_all": "清除全部", "image_split": "分割图像...", "col_name": "名称", "col_pos": "位置", "confirm_del": "删除?", "confirm_clear": "清除所有?", "table_label": "辅助线列表:" }
        }
        return db.get(lang, db["en"])

    def change_unit(self, new_unit):
        self.unit = new_unit
        self.refresh_list()

    def set_krita_state(self, action_name, checkbox):
        if self._block_signals: return
        action = Krita.instance().action(action_name)
        if action and action.isChecked() != checkbox.isChecked(): action.trigger()

    def sync_checkboxes(self):
        self._block_signals = True
        for act_id, cb in [("view_show_guides", self.cb_show_guides), ("view_ruler", self.cb_show_rulers), 
                           ("view_lock_guides", self.cb_lock_guides), ("view_snap_to_guides", self.cb_snap_guides)]:
            a = Krita.instance().action(act_id)
            if a: cb.setChecked(a.isChecked())
        self._block_signals = False

    def trigger_action(self, name):
        a = Krita.instance().action(name)
        if a: a.trigger()

    def refresh_list(self):
        self._block_signals = True
        self.table.setRowCount(0)
        doc = Krita.instance().activeDocument()
        if doc:
            w, h = doc.width(), doc.height()
            for axis, guides in [('h', doc.horizontalGuides()), ('v', doc.verticalGuides())]:
                max_val = h if axis == 'h' else w
                for i, val in enumerate(guides):
                    row = self.table.rowCount(); self.table.insertRow(row)
                    name = self.custom_names.get((axis, i), f"{axis.upper()}-{i}")
                    
                    if self.unit == "%":
                        display_val = round((val / max_val) * 100, 2)
                    else:
                        display_val = int(val)

                    name_item = QTableWidgetItem(name); name_item.setData(32, (axis, i, "name"))
                    val_item = QTableWidgetItem(str(display_val)); val_item.setData(32, (axis, i, "pos"))
                    self.table.setItem(row, 0, name_item); self.table.setItem(row, 1, val_item)
        self.sync_checkboxes()
        self._block_signals = False

    def on_item_changed(self, item):
        if self._block_signals: return
        data = item.data(32)
        if not data: return
        axis, index, f_type = data
        doc = Krita.instance().activeDocument()
        if not doc: return
        
        if f_type == "name": 
            self.custom_names[(axis, index)] = item.text()
        else:
            try:
                val = float(item.text().replace(",", "."))
                w, h = doc.width(), doc.height()
                max_val = h if axis == 'h' else w
                
                if self.unit == "%":
                    pixel_val = (val / 100) * max_val
                else:
                    pixel_val = val
                
                g = doc.horizontalGuides() if axis == 'h' else doc.verticalGuides()
                if 0 <= index < len(g):
                    g[index] = pixel_val
                    if axis == 'h': doc.setHorizontalGuides(g)
                    else: doc.setVerticalGuides(g)
            except: pass
        self.refresh_list()

    def save_current_layout(self):
        doc = Krita.instance().activeDocument()
        if not doc: return
        name, ok = QInputDialog.getText(self, self.texts["save"], "Name:")
        if ok and name:
            self.saved_layouts[name] = {"h": doc.horizontalGuides(), "v": doc.verticalGuides(), "names": {str(k): v for k, v in self.custom_names.items()}}
            self.save_to_disk(); self.update_combo_box()

    def load_selected_layout(self):
        name = self.layout_selector.currentText()
        doc = Krita.instance().activeDocument()
        if name in self.saved_layouts and doc:
            data = self.saved_layouts[name]
            doc.setHorizontalGuides(data["h"]); doc.setVerticalGuides(data["v"])
            self.custom_names = {eval(k): v for k, v in data.get("names", {}).items()}
            self.refresh_list()

    def delete_selected_layout(self):
        name = self.layout_selector.currentText()
        if name.startswith("--"): return
        if QMessageBox.question(self, self.texts["delete"], self.texts["confirm_del"], QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if name in self.saved_layouts:
                del self.saved_layouts[name]; self.save_to_disk(); self.update_combo_box()

    def load_from_disk(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}

    def save_to_disk(self):
        try:
            with open(self.save_path, 'w', encoding='utf-8') as f: json.dump(self.saved_layouts, f, indent=4)
        except: pass

    def update_combo_box(self):
        self.layout_selector.clear()
        self.layout_selector.addItem(f"-- {self.texts['load']} --")
        for name in sorted(self.saved_layouts.keys()): self.layout_selector.addItem(name)

    def confirm_clear_all(self):
        if QMessageBox.question(self, "Reset", self.texts["confirm_clear"], QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            doc = Krita.instance().activeDocument()
            if doc: doc.setHorizontalGuides([]); doc.setVerticalGuides([]); self.custom_names = {}; self.refresh_list()

    def canvasChanged(self, canvas): self.refresh_list()

app = Krita.instance()
app.addDockWidgetFactory(DockWidgetFactory("exact_guides_docker", DockWidgetFactoryBase.DockRight, ExactGuidesDocker))