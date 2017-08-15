# -*- coding: utf-8 -*-
"""
Spyder Editor

@author: zamlty 2017.08.07
"""

from bs4 import BeautifulSoup
from io import BytesIO
from numpy import array
from PIL import Image
import os
import platform
import re
import requests
import sys
import time


def get_validate_code_img(session, url):
    threshold = 140
    table = [0] * threshold + [1] * (256 - threshold)
    im = Image.open(BytesIO(session.get(url + "ValidateCode.jsp").content)) \
              .convert("L").crop((1, 1, 59, 20)).point(table, "1")
    return im

def console_show_code(im, white_char=True):
    arr = (array(im) == white_char)
    for i in arr:
        for j in i:
            print((" " if j else u"\u2588") * 2, end="")
        print()


if __name__ == "__main__":
    # params
    url = "https://elite.nju.edu.cn/jiaowu/"
    data = {"userName": "abc", "password": "123"}
    GPA_max = 5.0
    width = 32
    white_char = True

    # initialize
    session = requests.session()

    # login
    while True:
        # validate code
        while True:
            im = get_validate_code_img(session, url)
            console_show_code(im, white_char)
            code = input("validate code: ")
            if code != "-1":
                break
        data["ValidateCode"] = code

        # confirm data
        r = session.post(url + "login.do", data)
        soup = BeautifulSoup(r.content, "lxml")
        error = soup.find(text=re.compile("错误"))
        if error:
            print(error)
            if "用户名或密码" in error:
                exit()
        else:
            os.system("cls" if platform.system() == "Windows" else "clear")
            break

    # print welcome
    user = soup.find(id="UserInfo").text.split()[0][4:]
    now = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime())
    print("Welcome {0}{2:>{1}}\n".format(user, 50-len(user.encode("gbk")), now))

    # get terms
    r = session.get(url + "student/studentinfo/achievementinfo.do?method=searchTermList")
    soup = BeautifulSoup(r.content, "lxml")
    terms = [{"year": td.text.strip(), "url": url + td.a["href"]} for td in
              soup.select("table tr td div table tr[align=center] td")][::-1]

    # weight for sorting
    weight = {"通修": 5, "平台": 4, "核心": 3, "选修": 2, "通识": 1, "公选": 0}

    # get data from each term
    for term in terms:
        year = term["year"]
        term["year"] = year[:9] + " " + year[9:]

        r = session.get(term["url"])
        soup = BeautifulSoup(r.content, "lxml")

        subjects = []
        sum_credit = dict.fromkeys(["all", "major", "通修", "平台", "核心",
                                    "选修", "通识", "公选"], 0)
        sum_sc = {"all": 0, "major": 0}

        # get data from each subject
        for tr in soup.select("table tr td table tr[align=left]"):
            _, num, name, _, tp, c, s, _, _ = map(lambda x: x.text.strip(),
                                                  tr.find_all("td"))

            name += " " * (width - len(name.encode("gbk")))
            c = int(c.split(".")[0])
            s = s.split(".")[0]

            if re.match("00[2-4]|500|37", num):
                tp = "通识"
            elif re.match("77|78|61", num):
                tp = "公选"

            if s.isdigit():
                s = int(s)

                if tp in ["通修", "平台", "核心"]:
                    sum_credit["major"] += c
                    sum_sc["major"] += s * c

                sum_credit[tp] += c
                sum_credit["all"] += c
                sum_sc["all"] += s * c

            subject = {"num": num, "name": name, "type": tp, "credit": c, "score": s}
            subjects.append(subject)

        subjects.sort(key=lambda s: weight[s["type"]] * 10 + s["credit"], reverse=True)

        term["subjects"] = subjects
        term["sum_credit"] = sum_credit
        term["sum_sc"] = sum_sc
        term["GPA"] = {
                "all": sum_sc["all"] / sum_credit["all"] * GPA_max / 100,
                "major": sum_sc["major"] / sum_credit["major"] * GPA_max / 100
                }

        term["text"] = """{0:>34}
GPA: {1[major]:5.3f} / {1[all]:5.3f}{2}总学分：{3:3}
""".format(term["year"], term["GPA"], " "*29, term["sum_credit"]["all"]) + \
"  ".join("{}：{:>2}".format(k, v) for k, v in list(sum_credit.items())[2:]) + \
"\n" + "\n".join("{0:0>2}    {1[name]}{1[type]:>6}{1[credit]:>6}{1[score]:>6}"
.format(i+1, s) for i, s in enumerate(subjects)) + "\n"

        print(term["text"])

    # sum data for terms
    terms_sum_credit =  dict.fromkeys(["all", "major", "通修", "平台", "核心",
                                       "选修", "通识", "公选"], 0)
    terms_sum_sc = {"all": 0, "major": 0}
    terms_GPA = {"all": 0, "major": 0}

    terms_sum_credit = {k: sum([t["sum_credit"][k] for t in terms])
                        for k in terms_sum_credit}
    terms_sum_sc = {k: sum([t["sum_sc"][k] for t in terms]) for k in terms_sum_sc}
    terms_GPA = {k: terms_sum_sc[k] / terms_sum_credit[k] * GPA_max / 100
                 for k in terms_GPA}

    terms_text = "GPA: {0[major]:5.3f} / {0[all]:5.3f}{1}总学分：{2:3}\n" \
                 .format(terms_GPA, " "*29, terms_sum_credit["all"]) + \
                 "  ".join("{}：{:>2}".format(k, v)
                            for k, v in list(terms_sum_credit.items())[2:])

    print(terms_text)
