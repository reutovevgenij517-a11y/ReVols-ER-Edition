
import os
import json
import html
import datetime
import traceback
import urllib.parse
from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window

from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

PythonActivity = None
for cls_name in (
    'org.renpy.android.PythonActivity',
    'org.kivy.android.PythonActivity',
    'ru.iiec.pydroid3.PythonActivity'
):
    try:
        PythonActivity = autoclass(cls_name)
        break
    except Exception:
        pass

Context = autoclass('android.content.Context')
LinearLayout = autoclass('android.widget.LinearLayout')
LayoutParams = autoclass('android.widget.LinearLayout$LayoutParams')
ViewGroupLayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
WindowManagerLayoutParams = autoclass('android.view.WindowManager$LayoutParams')
TextView = autoclass('android.widget.TextView')
EditText = autoclass('android.widget.EditText')
Button = autoclass('android.widget.Button')
ImageView = autoclass('android.widget.ImageView')
BitmapFactory = autoclass('android.graphics.BitmapFactory')
WebView = autoclass('android.webkit.WebView')
WebViewClient = autoclass('android.webkit.WebViewClient')
WebChromeClient = autoclass('android.webkit.WebChromeClient')
CookieManager = autoclass('android.webkit.CookieManager')
AlertDialogBuilder = autoclass('android.app.AlertDialog$Builder')
InputType = autoclass('android.text.InputType')
EditorInfo = autoclass('android.view.inputmethod.EditorInfo')
BuildVersion = autoclass('android.os.Build$VERSION')
Color = autoclass('android.graphics.Color')
Gravity = autoclass('android.view.Gravity')
String = autoclass('java.lang.String')

HISTORY_FILE = os.path.abspath("revols_history.json")
SEARCH_HISTORY_FILE = os.path.abspath("revols_search_history.json")
BOOKMARKS_FILE = os.path.abspath("revols_bookmarks.json")


class OnClickListener(PythonJavaClass):
    __javainterfaces__ = ['android/view/View$OnClickListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Landroid/view/View;)V')
    def onClick(self, view):
        self.callback(view)


class OnEditorActionListener(PythonJavaClass):
    __javainterfaces__ = ['android/widget/TextView$OnEditorActionListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Landroid/widget/TextView;ILandroid/view/KeyEvent;)Z')
    def onEditorAction(self, view, action_id, event):
        self.callback()
        return True


class DialogClickListener(PythonJavaClass):
    __javainterfaces__ = ['android/content/DialogInterface$OnClickListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Landroid/content/DialogInterface;I)V')
    def onClick(self, dialog, which):
        self.callback(dialog, which)
class RevolsERApp(App):
    def build(self):
        self.listeners = []
        self.root_layout = None
        self.webview = None
        self.url_input = None
        self.lbl_er = None
        self.btn_adblock = None
        self.adblock_enabled = False
        self.incognito_mode = False
        self.last_logged_url = ""
        self.history_list = self.load_json_list(HISTORY_FILE)
        self.search_history = self.load_json_list(SEARCH_HISTORY_FILE)
        self.custom_bookmarks = self.load_json_list(BOOKMARKS_FILE)

        Window.bind(on_keyboard=self.on_android_back)

        self.status_lbl = Label(text="Запуск ReVols ER Edition...", font_size="18sp")
        Clock.schedule_once(self.start_browser, 0.3)
        return self.status_lbl

    def on_pause(self):
        if not self.incognito_mode:
            try:
                CookieManager.getInstance().flush()
            except Exception:
                pass
        return True

    def on_android_back(self, window, key, *args):
        if key == 27:
            self.go_back()
            return True
        return False

    def load_json_list(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_json_list(self, filepath, data):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_to_history(self, url):
        if self.incognito_mode:
            return
        if not url or not url.startswith(("http://", "https://")):
            return
        if url == self.last_logged_url:
            return
        self.last_logged_url = url
        now_str = datetime.datetime.now().strftime("%d.%m %H:%M")
        self.history_list = [item for item in self.history_list if item.get("url") != url]
        self.history_list.insert(0, {"url": url, "time": now_str})
        self.history_list = self.history_list[:50]
        self.save_json_list(HISTORY_FILE, self.history_list)

    def add_to_search_history(self, query):
        if self.incognito_mode or not query:
            return
        now_str = datetime.datetime.now().strftime("%d.%m %H:%M")
        self.search_history = [item for item in self.search_history if item.get("query") != query]
        self.search_history.insert(0, {"query": query, "time": now_str})
        self.search_history = self.search_history[:40]
        self.save_json_list(SEARCH_HISTORY_FILE, self.search_history)

    def start_browser(self, dt):
        try:
            if PythonActivity is None:
                self.status_lbl.text = "Ошибка: не найден класс PythonActivity"
                return
            self.activity = PythonActivity.mActivity
            self.build_native_ui()
        except Exception:
            self.status_lbl.text = f"Ошибка запуска:\n{traceback.format_exc()}"

    def dp_to_px(self, dp_val):
        try:
            density = self.activity.getResources().getDisplayMetrics().density
            return int(dp_val * density)
        except Exception:
            return int(dp_val * 2.5)

    @run_on_ui_thread
    def hide_keyboard(self):
        try:
            imm = self.activity.getSystemService(Context.INPUT_METHOD_SERVICE)
            imm.hideSoftInputFromWindow(self.url_input.getWindowToken(), 0)
        except Exception:
            pass
    @run_on_ui_thread
    def exit_app(self):
        try:
            if not self.incognito_mode:
                CookieManager.getInstance().flush()
        except Exception:
            pass
        try:
            self.activity.finish()
        except Exception:
            pass
        self.stop()

    @run_on_ui_thread
    def build_native_ui(self):
        try:
            if BuildVersion.SDK_INT >= 28:
                try:
                    WebView.setDataDirectorySuffix(String("revols_er_webview"))
                except Exception:
                    pass

            win = self.activity.getWindow()
            win.clearFlags(
                WindowManagerLayoutParams.FLAG_NOT_FOCUSABLE |
                WindowManagerLayoutParams.FLAG_ALT_FOCUSABLE_IM
            )
            win.setSoftInputMode(WindowManagerLayoutParams.SOFT_INPUT_ADJUST_RESIZE)

            self.root_layout = LinearLayout(self.activity)
            self.root_layout.setOrientation(LinearLayout.VERTICAL)
            self.root_layout.setBackgroundColor(Color.parseColor("#090C10"))
            self.root_layout.setFocusableInTouchMode(True)

            header = LinearLayout(self.activity)
            header.setOrientation(LinearLayout.HORIZONTAL)
            header.setGravity(Gravity.CENTER_VERTICAL)
            header.setPadding(self.dp_to_px(8), self.dp_to_px(8), self.dp_to_px(8), self.dp_to_px(4))

            avatar_path = os.path.abspath("avatar.png")
            if os.path.exists(avatar_path):
                bitmap = BitmapFactory.decodeFile(avatar_path)
                if bitmap:
                    avatar_view = ImageView(self.activity)
                    avatar_view.setImageBitmap(bitmap)
                    avatar_params = LayoutParams(self.dp_to_px(32), self.dp_to_px(32))
                    avatar_params.setMargins(0, 0, self.dp_to_px(8), 0)
                    header.addView(avatar_view, avatar_params)

            lbl_revols = TextView(self.activity)
            lbl_revols.setText(String("ReVols "))
            lbl_revols.setTextSize(19.0)
            lbl_revols.setTextColor(Color.parseColor("#00E5FF"))
            header.addView(lbl_revols)

            self.lbl_er = TextView(self.activity)
            self.lbl_er.setText(String("ER"))
            self.lbl_er.setTextSize(17.0)
            self.lbl_er.setTextColor(Color.parseColor("#FF1744"))
            lbl_params = LayoutParams(0, ViewGroupLayoutParams.WRAP_CONTENT, 1.0)
            header.addView(self.lbl_er, lbl_params)

            btn_w = self.dp_to_px(38)
            btn_h = self.dp_to_px(38)
            margin_r = self.dp_to_px(4)

            self.btn_adblock = Button(self.activity)
            self.btn_adblock.setText(String("🛡️"))
            self.btn_adblock.setBackgroundColor(Color.parseColor("#1F2937"))
            self.btn_adblock.setTextColor(Color.GRAY)
            ad_listener = OnClickListener(lambda v: self.toggle_adblock())
            self.listeners.append(ad_listener)
            self.btn_adblock.setOnClickListener(ad_listener)
            ad_params = LayoutParams(btn_w, btn_h)
            ad_params.setMargins(0, 0, margin_r, 0)
            header.addView(self.btn_adblock, ad_params)

            btn_home = Button(self.activity)
            btn_home.setText(String("🏠"))
            btn_home.setBackgroundColor(Color.parseColor("#161B22"))
            btn_home.setTextColor(Color.parseColor("#00E5FF"))
            home_listener = OnClickListener(lambda v: self.show_home_screen())
            self.listeners.append(home_listener)
            btn_home.setOnClickListener(home_listener)
            home_params = LayoutParams(btn_w, btn_h)
            home_params.setMargins(0, 0, margin_r, 0)
            header.addView(btn_home, home_params)

            btn_hist = Button(self.activity)
            btn_hist.setText(String("📜"))
            btn_hist.setBackgroundColor(Color.parseColor("#161B22"))
            btn_hist.setTextColor(Color.parseColor("#FFD600"))
            hist_listener = OnClickListener(lambda v: self.show_history_screen())
            self.listeners.append(hist_listener)
            btn_hist.setOnClickListener(hist_listener)
            hist_params = LayoutParams(btn_w, btn_h)
            hist_params.setMargins(0, 0, margin_r, 0)
            header.addView(btn_hist, hist_params)

            btn_exit = Button(self.activity)
            btn_exit.setText(String("✕"))
            btn_exit.setBackgroundColor(Color.parseColor("#3B1519"))
            btn_exit.setTextColor(Color.parseColor("#FF1744"))
            exit_listener = OnClickListener(lambda v: self.exit_app())
            self.listeners.append(exit_listener)
            btn_exit.setOnClickListener(exit_listener)
            header.addView(btn_exit, LayoutParams(btn_w, btn_h))

            self.root_layout.addView(header)

            nav_bar = LinearLayout(self.activity)
            nav_bar.setOrientation(LinearLayout.HORIZONTAL)
            nav_bar.setGravity(Gravity.CENTER_VERTICAL)
            nav_bar.setPadding(self.dp_to_px(8), self.dp_to_px(4), self.dp_to_px(8), self.dp_to_px(6))

            nav_btn_w = self.dp_to_px(38)
            nav_btn_h = self.dp_to_px(42)

            btn_back = Button(self.activity)
            btn_back.setText(String("<"))
            btn_back.setBackgroundColor(Color.parseColor("#1F2937"))
            btn_back.setTextColor(Color.WHITE)
            back_listener = OnClickListener(lambda v: self.go_back())
            self.listeners.append(back_listener)
            btn_back.setOnClickListener(back_listener)
            back_params = LayoutParams(nav_btn_w, nav_btn_h)
            back_params.setMargins(0, 0, margin_r, 0)
            nav_bar.addView(btn_back, back_params)

            self.url_input = EditText(self.activity)
            self.url_input.setHint(String("Поиск или URL (icn = инкогнито)..."))
            self.url_input.setHintTextColor(Color.GRAY)
            self.url_input.setTextColor(Color.WHITE)
            self.url_input.setTextSize(14.0)
            self.url_input.setBackgroundColor(Color.parseColor("#161B22"))
            self.url_input.setSingleLine(True)
            self.url_input.setPadding(self.dp_to_px(10), self.dp_to_px(8), self.dp_to_px(10), self.dp_to_px(8))
            self.url_input.setInputType(
                InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_VARIATION_URI |
                InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            )
            self.url_input.setImeOptions(EditorInfo.IME_ACTION_GO)

            editor_listener = OnEditorActionListener(self.on_url_submit)
            self.listeners.append(editor_listener)
            self.url_input.setOnEditorActionListener(editor_listener)

            input_params = LayoutParams(0, nav_btn_h, 1.0)
            input_params.setMargins(0, 0, margin_r, 0)
            nav_bar.addView(self.url_input, input_params)

            btn_go = Button(self.activity)
            btn_go.setText(String("GO"))
            btn_go.setBackgroundColor(Color.parseColor("#FF1744"))
            btn_go.setTextColor(Color.WHITE)
            go_listener = OnClickListener(lambda v: self.on_url_submit())
            self.listeners.append(go_listener)
            btn_go.setOnClickListener(go_listener)
            nav_bar.addView(btn_go, LayoutParams(self.dp_to_px(46), nav_btn_h))

            self.root_layout.addView(nav_bar)

            self.webview = WebView(self.activity)
            settings = self.webview.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setDatabaseEnabled(True)
            settings.setSaveFormData(True)
            settings.setCacheMode(-1)
            settings.setLoadWithOverviewMode(True)
            settings.setUseWideViewPort(True)
            settings.setBuiltInZoomControls(True)
            settings.setDisplayZoomControls(False)
            settings.setUserAgentString(
                "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
            )

            cookie_manager = CookieManager.getInstance()
            cookie_manager.setAcceptCookie(True)
            try:
                cookie_manager.setAcceptThirdPartyCookies(self.webview, True)
            except Exception:
                pass

            self.webview.setWebViewClient(WebViewClient())
            self.webview.setWebChromeClient(WebChromeClient())

            wv_params = LayoutParams(ViewGroupLayoutParams.MATCH_PARENT, 0, 1.0)
            self.root_layout.addView(self.webview, wv_params)

            self.activity.setContentView(self.root_layout)
            self.show_home_screen()

            Clock.schedule_interval(self.sync_scripts_and_cookies, 1.2)

        except Exception:
            self.status_lbl.text = f"Ошибка UI:\n{traceback.format_exc()}"
    @run_on_ui_thread
    def show_add_site_dialog(self):
        try:
            builder = AlertDialogBuilder(self.activity)
            builder.setTitle(String("Добавить свой сайт"))

            container = LinearLayout(self.activity)
            container.setOrientation(LinearLayout.VERTICAL)
            pad = self.dp_to_px(16)
            container.setPadding(pad, self.dp_to_px(8), pad, self.dp_to_px(8))

            name_input = EditText(self.activity)
            name_input.setHint(String("Название (например: ВКонтакте)"))
            container.addView(name_input)

            url_input = EditText(self.activity)
            url_input.setHint(String("Адрес (например: vk.com)"))
            url_input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI)
            container.addView(url_input)

            builder.setView(container)

            def on_save(dialog, which):
                name = str(name_input.getText().toString()).strip()
                url = str(url_input.getText().toString()).strip()
                if url:
                    if not url.startswith(("http://", "https://")):
                        url = "https://" + url
                    if not name:
                        name = url.replace("https://", "").replace("http://", "").split("/")
                    self.custom_bookmarks.append({"name": name, "url": url})
                    self.save_json_list(BOOKMARKS_FILE, self.custom_bookmarks)
                    self.show_home_screen()

            save_listener = DialogClickListener(on_save)
            cancel_listener = DialogClickListener(lambda d, w: d.dismiss())
            self.listeners.extend([save_listener, cancel_listener])

            builder.setPositiveButton(String("Сохранить"), save_listener)
            builder.setNegativeButton(String("Отмена"), cancel_listener)
            builder.show()
        except Exception:
            pass

    def on_url_submit(self):
        raw_text = str(self.url_input.getText().toString()).strip()
        self.hide_keyboard()
        if not raw_text:
            return

        if raw_text.lower() == "icn":
            self.set_incognito(not self.incognito_mode)
            return
        if raw_text.lower().startswith("icn "):
            target = raw_text[4:].strip()
            self.set_incognito(True, target)
            return

        self.load_url(raw_text)

    @run_on_ui_thread
    def load_url(self, query):
        query = query.strip()
        if not query:
            return

        if query.startswith("revols://history"):
            self.show_history_screen()
            return
        if query.startswith("revols://home"):
            self.show_home_screen()
            return

        if "." in query and " " not in query:
            if not query.startswith(("http://", "https://")):
                query = "https://" + query
            final_url = query
        else:
            self.add_to_search_history(query)
            encoded = urllib.parse.quote(query)
            final_url = f"https://duckduckgo.com{encoded}"

        self.url_input.setText(String(final_url))
        self.webview.loadUrl(String(final_url))

    @run_on_ui_thread
    def go_back(self):
        if self.webview and self.webview.canGoBack():
            self.webview.goBack()
        else:
            self.show_home_screen()
    @run_on_ui_thread
    def show_home_screen(self):
        self.url_input.setText(String(""))

        custom_tiles = ""
        for idx, bm in enumerate(self.custom_bookmarks):
            b_name = html.escape(bm.get("name", "Сайт"))
            b_url = html.escape(bm.get("url", ""))
            first_letter = html.escape(b_name[:1].upper() if b_name else "★")
            custom_tiles += f"""
            <div class="tile-wrap">
                <a class="tile" href="{b_url}">
                    <div class="tile-badge" style="background:#1A2433;color:#00E5FF;">{first_letter}</div>
                    <div class="tile-name">{b_name}</div>
                    <div class="tile-sub">Мой сайт</div>
                </a>
                <a class="del-btn" href="https://revols.del_bm{idx}">✕</a>
            </div>
            """

        recent_cards = ""
        if self.history_list:
            for item in self.history_list[:5]:
                raw_u = item.get("url", "")
                u = html.escape(raw_u)
                t = html.escape(item.get("time", ""))
                domain_parts = raw_u.replace("https://", "").replace("http://", "").split("/")
                domain = html.escape(domain_parts if domain_parts and domain_parts else raw_u)
                recent_cards += f"""
                <a class="recent-card" href="{u}">
                    <div class="recent-icon">🌐</div>
                    <div class="recent-info">
                        <div class="recent-domain">{domain}</div>
                        <div class="recent-url">{u[:42]}</div>
                    </div>
                    <div class="recent-time">{t}</div>
                </a>
                """
        else:
            recent_cards = '<div class="empty-note">Здесь появятся сайты, куда ты заходил</div>'

        home_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0; padding: 18px 14px 40px 14px;
                background: radial-gradient(circle at top, #131B26 0%, #090C10 75%);
                color: #E6EDF3; font-family: sans-serif;
            }}
            .hero {{
                text-align: center; padding: 12px 10px 18px 10px;
                border-bottom: 1px solid #1F2937; margin-bottom: 16px;
            }}
            .hero-title {{ font-size: 24px; font-weight: 800; letter-spacing: 1px; }}
            .cyan {{ color: #00E5FF; }}
            .red {{ color: #FF1744; }}
            .hero-sub {{ font-size: 12px; color: #8B949E; margin-top: 6px; }}
            .section-head {{
                display: flex; justify-content: space-between; align-items: center;
                font-size: 12px; font-weight: 700; color: #8B949E;
                text-transform: uppercase; letter-spacing: 0.8px; margin: 14px 4px 10px 4px;
            }}
            .add-btn {{
                background: #161B22; color: #00E5FF; border: 1px solid #00E5FF;
                padding: 4px 10px; border-radius: 8px; text-decoration: none; font-size: 11px;
            }}
            .grid {{
                display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
            }}
            .tile-wrap {{ position: relative; }}
            .tile {{
                display: block; background: #161B22; border: 1px solid #26303D; border-radius: 14px;
                padding: 14px 6px; text-align: center; text-decoration: none; color: #fff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.35);
            }}
            .tile:active {{ transform: scale(0.96); border-color: #00E5FF; }}
            .del-btn {{
                position: absolute; top: 5px; right: 6px; width: 20px; height: 20px;
                line-height: 20px; text-align: center; border-radius: 50%;
                background: #3B1519; color: #FF1744; font-size: 11px; text-decoration: none; font-weight: bold;
            }}
            .tile-badge {{
                width: 42px; height: 42px; line-height: 42px; margin: 0 auto 8px auto;
                border-radius: 12px; font-size: 20px; font-weight: bold;
            }}
            .tile-name {{ font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .tile-sub {{ font-size: 10px; color: #8B949E; margin-top: 2px; }}
            .recent-card {{
                display: flex; align-items: center; gap: 10px;
                background: #12171F; border: 1px solid #21262D; border-radius: 10px;
                padding: 10px 12px; margin-bottom: 8px; text-decoration: none; color: #fff;
            }}
            .recent-icon {{ font-size: 18px; }}
            .recent-info {{ flex: 1; overflow: hidden; }}
            .recent-domain {{ font-size: 14px; font-weight: bold; color: #00E5FF; }}
            .recent-url {{ font-size: 11px; color: #8B949E; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .recent-time {{ font-size: 11px; color: #6E7681; }}
            .empty-note {{ text-align: center; color: #6E7681; font-size: 13px; padding: 16px; }}
        </style>
        </head>
        <body>
            <div class="hero">
                <div class="hero-title"><span class="cyan">ReVols</span> <span class="red">ER EDITION</span></div>
                <div class="hero-sub">Аккаунты сохраняются • Антиреклама • Инкогнито (icn)</div>
            </div>

            <div class="section-head">
                <span>Быстрые сервисы</span>
                <a class="add-btn" href="https://revols.add_bm">➕ Добавить сайт</a>
            </div>
            <div class="grid">
                <a class="tile" href="https://discord.com">
                    <div class="tile-badge" style="background:#23274D;color:#5865F2;">💬</div>
                    <div class="tile-name">Discord</div>
                    <div class="tile-sub">discord.com</div>
                </a>
                <a class="tile" href="https://youtube.com">
                    <div class="tile-badge" style="background:#3B1519;color:#FF0033;">▶</div>
                    <div class="tile-name">YouTube</div>
                    <div class="tile-sub">youtube.com</div>
                </a>
                <a class="tile" href="https://spotify.com">
                    <div class="tile-badge" style="background:#123322;color:#1DB954;">🎵</div>
                    <div class="tile-name">Spotify</div>
                    <div class="tile-sub">spotify.com</div>
                </a>
                <a class="tile" href="https://google.com">
                    <div class="tile-badge" style="background:#1E293B;color:#4285F4;">G</div>
                    <div class="tile-name">Google</div>
                    <div class="tile-sub">google.com</div>
                </a>
                <a class="tile" href="https://duckduckgo.com">
                    <div class="tile-badge" style="background:#3A2218;color:#DE5833;">🦆</div>
                    <div class="tile-name">DuckDuckGo</div>
                    <div class="tile-sub">Поиск</div>
                </a>
                {custom_tiles}
            </div>

            <div class="section-head"><span>Недавние сайты</span></div>
            {recent_cards}
        </body>
        </html>
        """
        self.webview.loadDataWithBaseURL(
            String("https://revols.home"),
            String(home_html),
            String("text/html"),
            String("UTF-8"),
            None
        )
    @run_on_ui_thread
    def show_history_screen(self):
        self.url_input.setText(String("revols://history"))

        search_html = ""
        if self.search_history:
            for item in self.search_history:
                q_raw = item.get("query", "")
                q = html.escape(q_raw)
                t = html.escape(item.get("time", ""))
                search_url = f"https://duckduckgo.com{urllib.parse.quote(q_raw)}"
                search_html += f"""
                <a class="hist-item" href="{search_url}">
                    <div class="search-q">🔍 {q}</div>
                    <div class="hist-time">{t}</div>
                </a>
                """
        else:
            search_html = '<div class="empty">История поиска пуста</div>'

        items_html = ""
        if self.history_list:
            for item in self.history_list:
                u = html.escape(item.get("url", ""))
                t = html.escape(item.get("time", ""))
                items_html += f"""
                <a class="hist-item" href="{u}">
                    <div class="hist-url">🌐 {u}</div>
                    <div class="hist-time">{t}</div>
                </a>
                """
        else:
            items_html = '<div class="empty">История сайтов пуста</div>'

        hist_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 16px; background: #090C10; color: #E6EDF3; font-family: sans-serif; }}
            .top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
            h2 {{ margin: 0; color: #FFD600; font-size: 19px; }}
            h3 {{ margin: 18px 0 10px 0; color: #8B949E; font-size: 13px; text-transform: uppercase; }}
            .clear-btn {{
                background: #3B1519; color: #FF1744; border: 1px solid #FF1744;
                padding: 7px 12px; border-radius: 8px; text-decoration: none; font-size: 12px; font-weight: bold;
            }}
            .hist-item {{
                display: block; background: #161B22; border: 1px solid #26303D;
                border-radius: 10px; padding: 11px; margin-bottom: 8px; text-decoration: none;
            }}
            .search-q {{ color: #FFD600; font-size: 14px; font-weight: 600; }}
            .hist-url {{ color: #00E5FF; font-size: 13px; word-break: break-all; }}
            .hist-time {{ color: #8B949E; font-size: 11px; margin-top: 4px; }}
            .empty {{ color: #6E7681; font-size: 13px; padding: 10px 0; }}
        </style>
        </head>
        <body>
            <div class="top">
                <h2>📜 История</h2>
                <a class="clear-btn" href="https://revols.clear">Очистить всё</a>
            </div>
            <h3>🔍 История поиска</h3>
            {search_html}
            <h3>🌐 Посещённые сайты</h3>
            {items_html}
        </body>
        </html>
        """
        self.webview.loadDataWithBaseURL(
            String("https://revols.history"),
            String(hist_html),
            String("text/html"),
            String("UTF-8"),
            None
        )

    @run_on_ui_thread
    def set_incognito(self, enable, target_url=None):
        self.incognito_mode = enable
        settings = self.webview.getSettings()
        cookie_manager = CookieManager.getInstance()

        if self.incognito_mode:
            cookie_manager.flush()
            cookie_manager.setAcceptCookie(False)
            settings.setDomStorageEnabled(False)
            settings.setDatabaseEnabled(False)
            settings.setSaveFormData(False)
            settings.setCacheMode(2)

            self.root_layout.setBackgroundColor(Color.parseColor("#1D1128"))
            self.lbl_er.setText(String("🕵️ INCOGNITO"))
            self.lbl_er.setTextColor(Color.parseColor("#D500F9"))
            self.url_input.setHint(String("🕵️ Инкогнито (icn = выход)..."))
        else:
            self.webview.clearCache(True)
            self.webview.clearHistory()
            self.webview.clearFormData()

            cookie_manager.setAcceptCookie(True)
            try:
                cookie_manager.setAcceptThirdPartyCookies(self.webview, True)
            except Exception:
                pass
            settings.setDomStorageEnabled(True)
            settings.setDatabaseEnabled(True)
            settings.setSaveFormData(True)
            settings.setCacheMode(-1)

            self.root_layout.setBackgroundColor(Color.parseColor("#090C10"))
            self.lbl_er.setText(String("ER"))
            self.lbl_er.setTextColor(Color.parseColor("#FF1744"))
            self.url_input.setHint(String("Поиск или URL (icn = инкогнито)..."))

        if target_url:
            self.load_url(target_url)
        else:
            self.show_home_screen()

    @run_on_ui_thread
    def toggle_adblock(self):
        self.adblock_enabled = not self.adblock_enabled
        if self.adblock_enabled:
            self.btn_adblock.setBackgroundColor(Color.parseColor("#00C853"))
            self.btn_adblock.setTextColor(Color.WHITE)
            self.sync_scripts_and_cookies(0)
        else:
            self.btn_adblock.setBackgroundColor(Color.parseColor("#1F2937"))
            self.btn_adblock.setTextColor(Color.GRAY)
            if self.webview:
                self.webview.reload()

    def sync_scripts_and_cookies(self, dt):
        if not self.webview:
            return
        self._inject_page_scripts()

    @run_on_ui_thread
    def _inject_page_scripts(self):
        try:
            cur_raw = self.webview.getUrl()
            if not cur_raw:
                return
            cur_url = str(cur_raw.toString() if hasattr(cur_raw, "toString") else cur_raw)

            if cur_url.startswith("https://revols.add_bm"):
                self.show_home_screen()
                self.show_add_site_dialog()
                return

            if cur_url.startswith("https://revols.del_bm"):
                try:
                    idx = int(cur_url.split("https://revols.del_bm").strip("/"))
                    if 0 <= idx < len(self.custom_bookmarks):
                        self.custom_bookmarks.pop(idx)
                        self.save_json_list(BOOKMARKS_FILE, self.custom_bookmarks)
                except Exception:
                    pass
                self.show_home_screen()
                return

            if cur_url.startswith("https://revols.clear"):
                self.history_list = []
                self.search_history = []
                self.save_json_list(HISTORY_FILE, self.history_list)
                self.save_json_list(SEARCH_HISTORY_FILE, self.search_history)
                self.show_history_screen()
                return

            if cur_url.startswith(("http://", "https://")) and not cur_url.startswith(("https://revols.home", "https://revols.history")):
                self.add_to_history(cur_url)
                if not self.url_input.hasFocus():
                    self.url_input.setText(String(cur_url))

            if not self.incognito_mode:
                CookieManager.getInstance().flush()

            if self.adblock_enabled:
                js_code = """
                (function() {
                    var adSelectors = [
                        'ins.adsbygoogle', '[id*="google_ads"]', '[id*="yandex_rtb"]',
                        '[class*="yandex_rtb"]', '[class*="ad-banner"]', '[class*="adsbox"]',
                        '[class*="advert"]', '[class*="sponsored"]', '[data-testid="ad"]',
                        'iframe[src*="doubleclick"]', 'iframe[src*="googlesyndication"]',
                        'iframe[src*="yandex"]', 'iframe[src*="adfox"]', 'iframe[src*="ads"]',
                        '.b-banner', '.serp-adv-item'
                    ];
                    adSelectors.forEach(function(sel) {
                        try {
                            document.querySelectorAll(sel).forEach(function(el) {
                                el.style.setProperty('display', 'none', 'important');
                                el.remove();
                            });
                        } catch(e) {}
                    });
                })();
                """
                self.webview.evaluateJavascript(String(js_code), None)
        except Exception:
            pass


if __name__ == "__main__":
    RevolsERApp().run()
