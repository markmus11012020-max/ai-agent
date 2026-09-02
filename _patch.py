import pathlib
p = pathlib.Path(r"d:\AI-agent\aggregators\multitour_adapter.py")
src = p.read_text(encoding="utf-8")
PH = {
    "\u0442\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442": "\u0442\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442",
    "\u041d\u0435 \u0437\u0430\u0434\u0430\u043d MULTITOUR_TOKEN (\u0438\u043b\u0438 API_KEY) \u0432 .env \u2014 ": "\u041d\u0435 \u0437\u0430\u0434\u0430\u043d MULTITOUR_TOKEN (\u0438\u043b\u0438 API_KEY) \u0432 .env \u2014 ",
    "\u043f\u043e\u043b\u0443\u0447\u0438\u0442\u0435 \u0442\u043e\u043a\u0435\u043d \u0432 \u043b\u0438\u0447\u043d\u043e\u043c \u043a\u0430\u0431\u0438\u043d\u0435\u0442\u0435 Multitour.ru.": "\u043f\u043e\u043b\u0443\u0447\u0438\u0442\u0435 \u0442\u043e\u043a\u0435\u043d \u0432 \u043b\u0438\u0447\u043d\u043e\u043c \u043a\u0430\u0431\u0438\u043d\u0435\u0442\u0435 Multitour.ru.",
    "\u0421\u0435\u0442\u0435\u0432\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430: {exc}": "\u0421\u0435\u0442\u0435\u0432\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430: {exc}",
    "\u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430": "\u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430",
}
def fix(s):
    for k, v in PH.items():
        s = s.replace(k, v)
    return s
old = fix(
    "    # ---------- \u0442\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442 ----------\n"
    "    def _call(self, method: str, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n"
    "        if not self.token:\n"
    "            raise MultitourAPIError(\n"
    "                \"\u041d\u0435 \u0437\u0430\u0434\u0430\u043d MULTITOUR_TOKEN (\u0438\u043b\u0438 API_KEY) \u0432 .env \u2014 \"\n"
    "                \"\u043f\u043e\u043b\u0443\u0447\u0438\u0442\u0435 \u0442\u043e\u043a\u0435\u043d \u0432 \u043b\u0438\u0447\u043d\u043e\u043c \u043a\u0430\u0431\u0438\u043d\u0435\u0442\u0435 Multitour.ru.\"\n"
    "            )\n"
    "        payload = {\n"
    "            \"header\": {\"token\": self.token, \"method\": method},\n"
    "            \"request\": request or {},\n"
    "        }\n"
    "        try:\n"
    "            resp = self.session.post(\n"
    "                self.base_url, json=payload, timeout=self.timeout\n"
    "            )\n"
    "        except requests.RequestException as exc:\n"
    "            raise MultitourAPIError(f\"\u0421\u0435\u0442\u0435\u0432\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430: {exc}\") from exc\n"
    "        if resp.status_code != 200:\n"
    "            raise MultitourAPIError(\n"
    "                f\"HTTP {resp.status_code}: {resp.text[:300]}\"\n"
    "            )\n"
    "        try:\n"
    "            data = resp.json()\n"
    "        except ValueError as exc:\n"
    "            raise MultitourAPIError(\n"
    "                f\"JSON parse error: {exc}\\n{resp.text[:300]}\"\n"
    "            ) from exc\n"
    "        if not data.get(\"is_success\", False):\n"
    "            raise MultitourAPIError(\n"
    "                \"Multitour: \" + \"; \".join(data.get(\"error\") or [\"\u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430\"])\n"
    "            )\n"
    "        return data.get(\"response\") or {}\n"
)
new = open(r"d:\AI-agent\_newblock.txt", "r", encoding="utf-8").read()
assert old in src, "OLD not in src"
p.write_text(src.replace(old, new, 1), encoding="utf-8")
print("OK")
