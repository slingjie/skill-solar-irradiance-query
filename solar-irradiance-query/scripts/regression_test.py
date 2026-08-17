#!/usr/bin/env python3
"""solar-irradiance-query 回归测试：比对实时 API 返回与语料期望值。
用法: python3 scripts/regression_test.py   (需要 AMAP_WEBSERVICE_KEY, 自动找环境文件)
容差: 数值 ±3%；高德编码坐标严格要求（行政区划中心稳定）。
退出码: 0=全部通过, 1=存在失败。
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request

TOL = 0.03
HERE = os.path.dirname(os.path.abspath(__file__))

def key():
    k = os.environ.get("AMAP_WEBSERVICE_KEY", "")
    if k: return k
    for env in ("~/.hermes/.env", "~/.hermes/profiles/coding/.env"):
        p = os.path.expanduser(env)
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("AMAP_WEBSERVICE_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"\'')
    return ""

def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(2)
    raise last

def geocode(addr, city, k):
    u = (f"https://restapi.amap.com/v3/geocode/geo?address={urllib.parse.quote(addr)}"
         f"&city={urllib.parse.quote(city)}&output=JSON&key={k}")
    return get(u)

def lta(lat, lng):
    return get(f"https://api.globalsolaratlas.info/data/lta?loc={lat},{lng}").get("annual", {}).get("data", {})

def pvcalc(loc, ptype, cap, tilt, az, gmt):
    r = subprocess.run([sys.executable, os.path.join(HERE, "gsa_pvcalc.py"), "--loc", loc,
                        "--type", ptype, "--capacity", str(cap), "--tilt", str(tilt),
                        "--azimuth", str(az), "--gmt-offset", str(gmt), "--format", "json"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("gsa_pvcalc.py: " + r.stderr.strip()[-300:])
    return json.loads(r.stdout)

passed, failed = [], []
def check(name, cond, detail):
    (passed if cond else failed).append((name, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")

def near(actual, expect, tol=TOL):
    return abs(actual - expect) <= expect * tol

def main():
    k = key()
    assert k, "需要 AMAP_WEBSERVICE_KEY（环境变量或 ~/.hermes/.env）"
    print("== Case 1 [模式A·中文地址] 杭州市西湖区 ==")
    d = geocode("杭州市西湖区", "杭州", k)
    loc = d["geocodes"][0]["location"]
    lng, lat = loc.split(",")
    check("高德编码坐标", near(float(lng), 120.130396, 0.0005) and near(float(lat), 30.259242, 0.0005),
          f"{loc} (期望 120.130396,30.259242)")
    a = lta(lat, lng)
    check("GHI", near(a["GHI"], 1292.2), f"{a['GHI']:.1f} vs 1292.2")
    check("DNI", near(a["DNI"], 770.1), f"{a['DNI']:.1f} vs 770.1")
    check("OPTA", a["OPTA"] == 23, f"{a['OPTA']} vs 23")
    check("PVOUT_csi", near(a["PVOUT_csi"], 1114.1), f"{a['PVOUT_csi']:.1f} vs 1114.1")

    print("== Case 2 [模式A·直接坐标] 上海 ==")
    a = lta("31.2304", "121.4737")
    check("GHI", near(a["GHI"], 1324.6), f"{a['GHI']:.1f} vs 1324.6")
    check("DNI", near(a["DNI"], 821.2), f"{a['DNI']:.1f} vs 821.2")
    check("OPTA", a["OPTA"] == 25, f"{a['OPTA']} vs 25")
    check("PVOUT_csi", near(a["PVOUT_csi"], 1166.1), f"{a['PVOUT_csi']:.1f} vs 1166.1")

    print("== Case 3 [模式B·中文地址+PV] 深圳南山 medium 100kWp ==")
    d = geocode("深圳市南山区", "深圳", k)
    loc = d["geocodes"][0]["location"]
    lng, lat = loc.split(",")
    opta = lta(lat, lng)["OPTA"]
    check("深圳 OPTA", opta == 19, f"{opta} vs 19")
    out = pvcalc(f"{lat},{lng}", "medium", 100, opta, 180, 28800)
    ann = out["annual"]["data"]; mon = out["monthly"]["data"]["PVOUT_total"]
    check("年发电量", near(ann["PVOUT_total"], 123363), f"{ann['PVOUT_total']:,.0f} vs 123,363")
    check("7月", near(mon[6], 12091), f"{mon[6]:,.0f} vs 12,091")
    check("不变量:月合计=年值", abs(sum(mon) - ann["PVOUT_total"]) <= max(1, ann["PVOUT_total"]*1e-6),
          f"{sum(mon):,.0f} vs {ann['PVOUT_total']:,.0f}")

    print("== Case 4 [模式B·海外] 越南河内 gmt 25200 ==")
    out = pvcalc("21.0285,105.8542", "medium", 100, 15, 180, 25200)
    ann = out["annual"]["data"]; mon = out["monthly"]["data"]["PVOUT_total"]
    check("年发电量", near(ann["PVOUT_total"], 106085), f"{ann['PVOUT_total']:,.0f} vs 106,085")
    check("7月", near(mon[6], 10839), f"{mon[6]:,.0f} vs 10,839")
    check("不变量:月合计=年值", abs(sum(mon) - ann["PVOUT_total"]) <= max(1, ann["PVOUT_total"]*1e-6),
          f"{sum(mon):,.0f} vs {ann['PVOUT_total']:,.0f}")

    print("== Case 5 [异常路径] ==")
    a = lta("0", "150")
    check("海洋坐标仍返回数据(坑①成立)", a.get("GHI") is not None, f"GHI={a.get('GHI'):.1f} → 需人工判断")
    try:
        lta("120.13", "30.26")
        check("非法纬度报错", False, "意外返回数据")
    except Exception as e:
        check("非法纬度报错(HTTP 500)", getattr(e, "code", None) == 500, f"{type(e).__name__} {getattr(e,'code','?')}")

    print()
    print(f"结果: {len(passed)} 通过 / {len(failed)} 失败")
    for name, detail in failed:
        print(f"  FAIL {name}: {detail}")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()