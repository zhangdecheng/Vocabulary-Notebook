#!/usr/bin/env python3
"""Append the 2026-11-02..11-08 side story to stories.html.

Does not edit words.json / words.js / bounds.js / anki.html / index.html / audio.
New cards live in site/data/week-1102.js and are not part of the main word list.
No IPA and no audio are invented. Paragraph and word play controls are omitted.
"""
import hashlib, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build", "week-1102")
SITE = os.path.join(ROOT, "site")

CHAPTERS = [
    (70, "A New Study Plan", "周一：新的学习计划", "11/02",
     "Leo 想去国外找工作，先和老师 Ms. Rina 重新制定学习方法：少被动灌输，多自学和独立思考。"),
    (71, "Applying for a Job Abroad", "周二：一份海外求职申请", "11/03",
     "课堂模拟海外求职：选城市、填网申表、谈优缺点和性格，再了解五步招聘流程。"),
    (72, "The Contract, School, and a Hot Room", "周三：合同、学校和闷热的房间", "11/04",
     "谈拿到 offer 之后的试用期和合同，回忆学生时代的科目，吐槽闷热的房间，并识别一个可疑的订房网站。"),
    (73, "Planning a Short Trip", "周四：旅行计划", "11/05",
     "Leo 通过了网申第一步，和 Ken 计划一次小旅行庆祝，聊目的地、交通费用和想家的心情。"),
    (74, "The Film Set and the Proposal", "周五：片场、演唱会和一次求婚", "11/06",
     "晒伤和纹身的小插曲，参观片场学到 “fire in the hole” 的真实含义，晚上海边公园演唱会上遇到一场求婚。"),
]
SUBS = {
    "2.1 Choosing a city": "选一座城市",
    "2.2 The online form": "网上申请表",
    "2.3 Strengths and weaknesses": "优点和缺点",
    "2.4 Different paths": "不同的路",
    "2.5 Five steps": "五个步骤",
    "3.1 After the offer": "拿到 offer 之后",
    "3.2 School days": "学生时代",
    "3.3 The hot room": "闷热的房间",
    "3.4 A suspicious website": "可疑的网站",
    "5.1 Sunburn and a tattoo": "晒伤和纹身",
    "5.2 On a film set": "在片场",
    "5.3 The concert": "演唱会",
    "5.4 Home again": "回到家",
}
# Citation form on the card. Inflections stay as the lemma in `word`.
# Phrases that were corrected in the story use the natural expression.
CITATION = {
    "taurus": "Taurus",
    "hot and wet": "hot and humid",
    "extend contract": "extend your contract",
    "basic action": "basic movement",
    "sign contract": "sign a contract",
    "longer times": "it takes longer",
    "create new": "create a new list",
    "guy in concert": "a guy at the concert",
    "view spot": "viewing spot",
    "in free time": "in my free time",
    "mosquito": "mosquito bites",
}
NOTES = {
    "taurus": "星座名写作 Taurus，符号是 bull（公牛）。",
    "hot and wet": "形容天气或房间又热又潮，说 hot and humid。",
    "extend contract": "说 extend your contract。合同快到期时可以谈延长；通过试用期并不等于一定会续约。",
    "basic action": "舞蹈里的基本动作说 basic movement。",
    "sign contract": "说 sign a contract。",
    "longer times": "表示花的时间更长，说 it takes longer。",
    "create new": "说 create a new list，不单独说 create new。",
    "guy in concert": "说 a guy at the concert。",
    "view spot": "说 viewing spot。",
    "in free time": "说 in my free time。",
    "mosquito": "本课说的是 mosquito bites，蚊子包。",
    "faithful": "这里指狗对主人。说人在职场忠诚，更常用 loyal。",
    "talking": "这里指和考官交谈。口语技能这个名字一般用 speaking。",
    "fire in the hole": "爆破前的安全警告。只在受控的表演里出现，不要随便喊。",
    "Mewali": "巴厘语，不是本课的英语词。释义尚未核验，请先问巴厘语使用者。",
}

ZH = [
"星期一，新一周的第一天。Leo 有个大计划：他想去国外找工作。不过首先，他的英语得更好才行。",
"“我们先热身，”他的英语老师 Ms. Rina 说，“和 Ken 用五分钟聊聊你的周末。”",
"热身之后，她给 Leo 看一张表。“这是 CEFR 等级。它可以给你方向。你现在是 B1，目标是 B2。”",
"Leo 很诚实：“在我以前的学校，什么都是填鸭式灌给你的。老师讲，我们抄。”",
"“很多把英语当第二语言来学的人都这么说，”Ms. Rina 回答，“可是抄写不是好的学习方法。你还需要自学和独立思考。”",
"“有时候以前的教室感觉像监狱，”Leo 笑着说，“作业则像惩罚。”",
"“这里不是那样，”她笑了笑，“我们先看看什么适合你，再把你的一天安排成三部分。”他们一起定下固定的练习时间：每天早上一个小时。",
"“你不用这个月就把一切都掌握，”她说，“但请不要马虎。交作业前先检查拼写。”",
"Ken 加入他们。“我靠带英文字幕的韩剧学英语。我表哥学法语也是这个办法。”",
"“好主意，”Ms. Rina 说，“也许你们俩可以组成一个学习小组。”",
"又做了一小回合口语练习之后，Leo 看着笔记本。他看到更早一课里的一个词：Mewali。“这是什么意思？”他问。“这是我们课堂笔记里的一个巴厘语词，”Ms. Rina 说，“我不确定确切意思。用之前，我们先问问会巴厘语的朋友。”",
"那天晚上，Leo 在 Instagram 上发了一条快拍，讲他的新计划。“分享你最喜欢的学习技巧！”他写道。很多朋友点了赞，有人收藏了，还有十个新的人关注了他。",
"星期二，Ms. Rina 问：“想象你申请另一个国家的工作。你怎么选城市？”",
"Ken 先答：“当然是高薪！我喜欢大城市。”",
"Leo 想了想：“钱是一个因素。但我也看天气、空气污染和房租。生活成本低对我很重要。在特别贵的城市里谋生很难。”",
"“在巴厘岛，我可以骑摩托车到任何地方，”他补了一句，“唯一的问题是蚊子。我身上总有很多蚊子包，胳膊也很痒。”",
"“所以对你来说，快乐比钱更重要？”Ms. Rina 问。“我两个都要，”Leo 笑了，“好收入和快乐的生活可以相辅相成。”",
"然后他们用一份网上申请表的样例来练习。“先把简历上传成 PDF，”Ms. Rina 说，“再填写个人资料。”",
"系统要 Leo 填国籍、所在地和性别。这张表上只有两个框：男和女。",
"下一项问：“你怀孕了吗？”Leo 停住了。“他们为什么要这个？这是私事。”他担心隐私，所以留空了。“你也可以给管理员发邮件，问他们为什么需要这项，”Ms. Rina 说。",
"“还要读要求，”她说，“有的工作需要大学文凭和英语考试成绩。再看看新闻：有没有针对你们国家的签证禁令？”",
"Leo 把各项都核对了一遍，然后点了提交。一分钟后，一封邮件到了：“请确认你的电子邮箱。”",
"“现在是面试，”Ms. Rina 说，“每个求职者都会听到这个问题：你的优点和缺点是什么？”",
"Leo 试着答：“我性格平静，桌子也总是很整洁。缺点？我有时很固执。”“这很诚实，”她说，“固执在团队里是一种风险，但也说明你不轻易放弃。”",
"“公司喜欢工作经历稳定的人，”她补充道，“他们不想要靠不住的人。”",
"Ken 咧嘴笑了：“我的星座是金牛座。符号是一头公牛。人家说金牛座的人慢，但很努力！”",
"“公牛？不是母牛？”Leo 开玩笑。Ms. Rina 笑了：“有人觉得每个星座都能代表一种性格。这次面试练习，我们还是看你的技能吧。”",
"“那我讲讲我的狗，”Ken 说，“他是我最忠实的朋友。每天都在门口等我。”",
"Ms. Rina 讲起以前的学生。“有一个是艺术家。他喜欢艺术，想进娱乐行业。他先去了表演学校。后来，伦敦一所戏剧学院录取了他。”",
"“另一个是程序员。他问我：‘我四十岁转行，是不是太老了？’我说不老。我总是鼓励人去试。每条路都有它特别的地方。”",
"“我的同学在一家鞋公司做销售，”Ken 说，“去年一位著名歌手答应给这双鞋代言。有些粉丝说这位歌手是为了钱出卖原则，因为那双鞋实在太丑了！”",
"Ms. Rina 在白板上画了一条线。她在线的上方写“申请”，下方写“得到工作”。“好工作的竞争很激烈，”她说，“练习的时候，我们假设一家公司有这五个步骤。”",
"1. 英语水平考试。它有听力部分和口语部分。口语部分就是和考官交谈。",
"2. 性格测试。",
"3. 体检。",
"4. 面试，对象包括人力资源、组长、经理，有时还有人力资源总监，甚至首席执行官。",
"5. 最后，你收到录用通知。",
"“谁做最后决定？”Leo 问。“通常是经理负责，”她说，“这个过程可能包含好几轮面试，要花好几周。心里记着你的目标。良好的沟通在每一步都有用，每一次面试都是成长的机会。”",
"下课后，Leo 把简历打印出来，放在房间里最高的架子上，免得被雨打湿。",
"星期三，Leo 问：“签了合同之后会发生什么？”",
"“通常，这份工作会先有一段试用期，”Ms. Rina 说，“也可以直接叫 probation。在这个语境里，probationary period 是 probation 的同义词。长短要看雇主和当地规定。你会接受培训，经理会衡量你的进展。”",
"“他们怎么衡量？”“靠评估。经理给你反馈，也可能写一份简短的报告。如果你通过试用期，就可以继续在那里工作。以后合同快到期时，公司可能会延长你的合同。”",
"“我也可以问面试官问题吗？”Leo 问。“请提问。你也可以上网查看这家公司的评价。”",
"“不要低估这份工作，也不要高估你自己，”她补充道，“签字之前，先看你会拿到的数额，以及工作的范围。问问自己：值不值？如果有什么让你觉得不公平，你可以拒绝。”",
"接着他们聊学校。Ken 在中国大陆长大。“高中时我们选文科或理科。我选了文科。我最喜欢的科目是政治。”",
"Leo 选了理科：数学、物理、生物和化学。“还有英语。不过我有一点懒。”",
"“成绩影响你的大学录取吗？”Ms. Rina 问。“有影响。我的考试排名不是很高，”Leo 说，“但它没有决定我的命运。”",
"“后来我在一所艺术学院学习。我上了舞蹈的工作室课程。每一个基本动作都可能要花好几周才能学会。”",
"“谁对你影响最大？”“我的舞蹈老师。她声音很轻，但很有纪律。她的教学方法很简单：每天练习。她的课程改变了我的人生。”",
"“你有一天想去外国的大学读书吗？”Ken 问。“也许吧，”Leo 说。",
"Leo 说起自己的房间。“又热又潮。没有通风，房间里满是蚊子。我不喜欢化学喷雾，所以买了一把电蚊拍。我挥它的样子，像在网球场上挥球拍。”",
"“你的家具多吗？”“只有一张床和一把钢椅子。不是很舒服。墙上有一幅黄色鸭子的画。在我们家，它是好运的象征。”",
"“上星期我有过一次糟糕的经历，”Leo 说，“我想在海滩附近订一家五星级酒店。我在一个网站上看到很好的价格。可是还没订完，它就要很多个人信息。我有一种奇怪的感觉。这很可疑。”",
"“有些人大批买下酒店房间再转手卖掉，”Ms. Rina 说，“有些网站就是骗局。一定要先在可信的应用里划着看真实评价。”",
"Ken 讲起他父亲。“我爸爸在汽车厂工作。”“也可以说 car plant，”Ms. Rina 说。",
"“昨晚我们看了一部拳击电影，”Ken 补了一句，“拳手的对家付钱让他故意输掉。意思是故意打输这场比赛。”“在电影里这很刺激，”Ms. Rina 说，“在现实里，这是作弊。”",
"星期四，Leo 收到一封邮件：他通过了第一步！为了庆祝，他和 Ken 计划一次短途旅行。",
"“我们去哪儿？”Ken 问，“也许越南？我想看历史景点，也想试试当地的餐馆。”",
"“我现在还不知道，”Leo 说，“老实说，我想放松。我想去安静的地方。”",
"“我们怎么去？”“这个月机票很贵。公共汽车更便宜，但花的时间更长。”“我们可以租一辆车。”“那还得付油费。”",
"“那我们买公共交通的票吧。更便宜，”Leo 说，“而且我得先再挣一点钱。”",
"Ken 安静下来。“我有点想家。一想家，我就没有胃口。”",
"“这很正常，”Ms. Rina 说，“去年我班上两个芬兰人也是这样。他们想念雪！其中一个甚至说我们以前的教室有鬼。”她笑了，“那只是风。”",
"然后她给 Leo 的作业打了一个好分数。",
"回到家，Leo 打开笔记应用，为这次旅行新建了一个清单。他看看自己的这一周。“我感到满意，”他说。",
"星期五，Leo 脖子晒伤了。“我在海滩待太久，没有防晒。”“戴顶帽子。你得保护皮肤，”Ms. Rina 说。Leo 的肤色现在深了一点。",
"Ken 给他们看一个新纹身。“我妈妈想说服我不要纹。她说我很叛逆，是个真正的叛逆者。”他笑了笑，“嗯，事情就是这样。”",
"Leo 说：“I very like it.” Ms. Rina 轻轻纠正他：“我们说 ‘I really like it.’。”",
"下午，他们去参观一个小片场。Ken 的表哥在那里工作。一位英俊的演员正在为动作戏排练，剧组准备开拍。戏里，一名士兵要把一枚假炸弹扔进一个洞。演员喊道：“Fire in the hole!”",
"导演解释：“在真实生活里，工人会在爆炸前这样喊，当作警告。这里只是表演，一切都在控制之中。请不要为了好玩这样喊。”然后假爆炸发出很大的响声。“太疯狂了！”Ken 说。",
"那天晚上，他们去海滩附近的公园听演唱会。他们把椅子搬到一个好的观景位置。一阵强风从海上吹来。演唱会上有个家伙在卖烤玉米，他们买了两份。",
"突然，音乐停了。一个男人和他的女朋友走上舞台。他一只手拿着一个小盒子，另一只手握住她的手。盒子里是一枚金色的戒指，上面有一颗小钻石。这是求婚！她答应了。人群大声欢呼，歌手喊道：“Peace and love!”",
"“时机太好了！”Leo 说。后来，求婚的视频在网上得到很多赞美。Leo 和 Ken 在舞台前摆姿势拍了照。“希望有一天，我也能邀请一个特别的人来这样的演唱会，”Leo 说。",
"回到家，Leo 饿了。他决定煮一块鱼。他用小烤箱的上方强热档。热量从上面来，鱼八分钟就好了。",
"晚饭后，外面的街道空荡荡的，很安静。Leo 想躺下。他在日记里写：“有空的时候，我想去更多这样的地方。这是很好的生活。”",
]


def esc(s):
    return html.escape(s, quote=True)


def short_gl(z):
    if "（" in z:
        head = z.split("（", 1)[0].strip()
        if len(head) >= 2:
            z = head
    if len(z) > 18 and "；" in z:
        z = z.split("；", 1)[0]
    if len(z) > 18:
        z = z[:17] + "…"
    return z


def meaning(item):
    if item["word"] == "Mewali":
        return "巴厘语词。释义尚未核验，本课不把它当作英语来教。"
    return item.get("meaning_context") or item.get("meaning_master") or ""


def learner_note(item):
    w = item["word"]
    if w in NOTES:
        return NOTES[w]
    n = item.get("note") or ""
    if n.startswith("缩写："):
        return n
    if n.startswith("本文义："):
        return n
    return ""


def headword(item):
    return CITATION.get(item["word"], item["word"])


def lesson_label(lesson):
    # 2026-11-02 -> 11/02
    m = re.match(r"\d{4}-(\d{2})-(\d{2})$", lesson or "")
    if not m:
        raise SystemExit("bad lesson " + str(lesson))
    return "%02d/%02d" % (int(m.group(1)), int(m.group(2)))


def load_story():
    text = open(os.path.join(SRC, "story.md"), encoding="utf-8").read()
    text = text.split("## 白板用词提示")[0]
    text = "## 第 1 章" + text.split("## 第 1 章", 1)[1]
    chs = []
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = {"blocks": []}
            chs.append(cur)
        elif line.startswith("### "):
            cur["blocks"].append(("S", line[4:].strip()))
        elif line.startswith("> ") or not line.strip():
            continue
        else:
            cur["blocks"].append(("P", line.strip()))
    if len(chs) != 5:
        raise SystemExit("expected 5 chapters, got %d" % len(chs))
    return chs


def render_para(md, item_iter, occ, chap_no, pi):
    parts = re.split(r"\*\*([^*]+)\*\*", md)
    out = []
    ids = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(esc(part))
            continue
        item = next(item_iter)
        if part != item["used_as"]:
            raise SystemExit("bold %r != used_as %r" % (part, item["used_as"]))
        sid = item["_id"]
        k = occ.get(sid, 0)
        occ[sid] = k + 1
        ids.append(sid)
        gl = "未核验" if item["word"] == "Mewali" else short_gl(meaning(item))
        cls = "tw w11u" if item["word"] == "Mewali" else "tw"
        out.append(
            '<span class="%s" data-i="%s" id="wk1102-%s-%d" tabindex="0">%s<i class="gl">%s</i></span>'
            % (cls, sid, sid, k, esc(part), esc(gl))
        )
    body = "".join(out)
    return (
        '<div class="para" id="c%dp%d"><p class="en" lang="en">%s</p><p class="zh" lang="zh">%s</p></div>'
        % (chap_no, pi, body, esc(ZH[item_iter.zh_i]))
    ), ids


class ItemIter:
    def __init__(self, items):
        self.items = iter(items)
        self.zh_i = -1

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.items)


def build():
    cov = json.load(open(os.path.join(SRC, "coverage.json"), encoding="utf-8"))
    items = cov["items"]
    if len(items) != 252 or len(ZH) != 75:
        raise SystemExit("count mismatch items %d zh %d" % (len(items), len(ZH)))
    for n, it in enumerate(items, 1):
        it["_id"] = "k1102-%03d" % n
        if not meaning(it) or "undefined" in meaning(it).lower():
            raise SystemExit("bad meaning " + it["word"])
        if it["word"] == "Mewali" and "不客气" in meaning(it):
            raise SystemExit("Mewali meaning must stay unverified")
    return build_clean(items)


def build_clean(items):
    chs_md = load_story()
    by_used = {}
    for it in items:
        if it["used_as"] in by_used:
            raise SystemExit("duplicate used_as " + it["used_as"])
        by_used[it["used_as"]] = it
    W, CH, CT = {}, {}, {}
    sections = []
    zh_i = 0
    for (no, title_en, title_zh, day, lead), md in zip(CHAPTERS, chs_md):
        CT[str(no)] = title_zh
        chunks = []
        order = []
        pi = 0
        occ = {}
        for kind, text in md["blocks"]:
            if kind == "S":
                zh = SUBS[text]
                chunks.append(
                    '<h3 class="w11sub"><span lang="en">%s</span><small>%s</small></h3>' % (esc(text), esc(zh))
                )
                continue
            parts = re.split(r"\*\*([^*]+)\*\*", text)
            out = []
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    out.append(esc(part))
                    continue
                item = by_used.get(part)
                if item is None:
                    raise SystemExit("ch %d bold %r has no coverage entry" % (no, part))
                sid = item["_id"]
                k = occ.get(sid, 0)
                occ[sid] = k + 1
                if sid not in order:
                    order.append(sid)
                z = meaning(item)
                gl = "未核验" if item["word"] == "Mewali" else short_gl(z)
                cls = "tw w11u" if item["word"] == "Mewali" else "tw"
                out.append(
                    '<span class="%s" data-i="%s" id="wk1102-%s-%d" tabindex="0">%s<i class="gl">%s</i></span>'
                    % (cls, sid, sid, k, esc(part), esc(gl))
                )
                if sid not in W:
                    note = learner_note(item)
                    rec = {
                        "w": headword(item),
                        "z": z,
                        "t": ["11/02–11/08 新词故事"],
                        "s": 0,
                        "g": note,
                        "d": [lesson_label(item["lesson"])],
                        "b": "2026-11-06 本地快照",
                        "h": no,
                        "c": 1,
                        "new": 0,
                        "na": 1,
                        "bt": "11/02–08",
                        "sf": part,
                    }
                    if item["word"] == "Mewali":
                        rec["u"] = 1
                    W[sid] = rec
                else:
                    W[sid]["c"] += 1
            if zh_i >= len(ZH):
                raise SystemExit("ran out of translations")
            chunks.append(
                '<div class="para" id="c%dp%d"><p class="en" lang="en">%s</p><p class="zh" lang="zh">%s</p></div>'
                % (no, pi, "".join(out), esc(ZH[zh_i]))
            )
            pi += 1
            zh_i += 1
        CH[str(no)] = order
        rows = []
        for sid in order:
            w = W[sid]
            rows.append(
                '<tr data-i="%s"><td class="wd"><a href="#" class="jump" data-i="%s">%s</a> <sup class="nwt bt">11/02–08</sup></td>'
                '<td class="ph">—</td><td class="pr"><span class="w11na">暂无</span></td><td class="mn">%s</td><td class="sr"></td>'
                '<td><label class="lk"><input type="checkbox" class="lrn" data-i="%s"><span>已掌握</span></label></td></tr>'
                % (sid, sid, esc(w["w"]), esc(w["z"]), sid)
            )
        sections.append(
            '<section class="chap w11" id="c%d" data-c="%d" data-week="2026-11-02">\n'
            '<header class="ch-h"><div class="ch-no">Chapter %d<span class="ch-th">11/02–11/08 新词故事</span><span class="ch-bt">11/02–08</span></div>\n'
            '<h2><span lang="en">%s</span><small>%s</small></h2>\n'
            '<p class="w11lead">%s</p>\n'
            '<div class="ch-meta"><span>%d 个词条</span><span>%s 课</span><span>%d 段</span><span class="na">暂无朗读</span><span class="ch-prog" data-cp="%d"></span></div></header>\n'
            '<div class="story">%s</div>\n'
            '<details class="wl" open><summary>本章词表 <small>%d 词 · 勾选「已掌握」自动保存 · 暂无音频 · 词义据 2026-11-06 本地快照</small></summary>'
            '<div class="tblw"><table><thead><tr><th>单词 / 表达</th><th>音标</th><th>发音</th><th>释义</th><th>★</th><th>掌握</th></tr></thead><tbody>%s</tbody></table></div></details>\n'
            '</section>\n'
            % (no, no, no, esc(title_en), esc(title_zh), esc(lead), len(order), day, pi, no, "".join(chunks), len(order), "".join(rows))
        )
    seen = {sid for ids in CH.values() for sid in ids}
    if len(seen) != len(items) or zh_i != len(ZH):
        raise SystemExit("unconsumed items %d/%d zh %d/%d" % (len(seen), len(items), zh_i, len(ZH)))
    if len(W) != 252:
        raise SystemExit("cards %d" % len(W))
    expect = {"第 %d 章" % (i + 1): no for i, (no, *_) in enumerate(CHAPTERS)}
    for it in items:
        prefix = it["chapter"].split("·", 1)[0].strip()
        if W[it["_id"]]["h"] != expect[prefix]:
            raise SystemExit("chapter mismatch %s -> %s" % (it["word"], prefix))
    return W, CH, CT, "".join(sections)


INTRO = """<section class="intro w11intro" id="w1102">
<h2>A Week of New Words <span class="ch-bt">11/02–11/08</span></h2>
<p>这是主线之外的一周番外，不是原来那些章节的改写。Leo 在这一周跟英语老师 Ms. Rina、同学 Ken 上课。人物和情节都是虚构的。</p>
<div class="cast"><div><b>Leo</b>想去国外找工作，这一周在补英语</div><div><b>Ms. Rina</b>这一周的英语老师</div><div><b>Ken</b>这一周的同学</div></div>
<p class="tip">下面 5 章写 2026-11-02 至 11-08 这一学习周。252 个词条来自 2026-11-06 的本地单词本快照（课次在 11/02–11/06；11/07 和 11/08 没有新课），还没有并入本站主词表。页头的词数仍只统计主词表。这一组暂无配套朗读和音标；词表里的「暂无」就是这个意思。巴厘语词 Mewali 的释义尚未核验，不当作英语词来教。</p>
</section>
"""

TOC = (
    '<div class="tg"><div class="tgh tgbt"><span class="sym">周</span>11/02–11/08 新词故事</div>'
    '<a href="#w1102">本组说明</a>'
    + "".join(
        '<a href="#c%d" data-c="%d"><b>%d</b> %s<small class="np" data-np="%d"></small></a>'
        % (no, no, no, esc(zh), no)
        for no, en, zh, day, lead in CHAPTERS
    )
    + "</div>"
)

CSS = """/*w11-css*/
.w11lead{margin:4px 0 12px;color:var(--mut);font-size:14.5px}
.w11sub{margin:18px 0 2px;font-family:var(--serif);font-size:18px;line-height:1.35;color:var(--acc)}
.w11sub small{display:block;font-family:var(--font);font-size:13px;color:var(--mut);font-weight:500}
.chap.w11 .zh{margin-left:0}
.chap.w11 .ch-meta span.na{background:#f3e6dc;color:#8a4a24}
.w11na{color:var(--mut);font-size:12.5px}
.tw.w11u{border-bottom-style:dashed}
html[data-theme=dark] .chap.w11 .ch-meta span.na{background:#3a2a22;color:#f0c2a0}
/* /w11-css*/"""


def patch(html_text, body):
    html_text = re.sub(r"<!--w11-toc-->.*?<!--/w11-toc-->", "", html_text, flags=re.S)
    html_text = re.sub(r"<!--w11-body-->.*?<!--/w11-body-->", "", html_text, flags=re.S)
    html_text = re.sub(r"/\*w11-css\*/.*?/\* /w11-css\*/", "", html_text, flags=re.S)
    html_text = re.sub(r'<script src="data/week-1102\.js\?v=[0-9a-f]+"></script>', "", html_text)
    if "<!--w11-toc-->" in html_text or 'id="w1102"' in html_text or 'id="c70"' in html_text:
        raise SystemExit("stale week markup still present")
    anchor = '<div class="tocf"></div>'
    if anchor not in html_text:
        raise SystemExit("toc anchor missing")
    html_text = html_text.replace(anchor, "<!--w11-toc-->" + TOC + "<!--/w11-toc-->" + anchor, 1)
    main = "\n</main>"
    if html_text.count(main) != 1:
        raise SystemExit("main anchor %d" % html_text.count(main))
    html_text = html_text.replace(main, "\n<!--w11-body-->\n" + INTRO + body + "<!--/w11-body-->\n</main>", 1)
    style = "</style><!--thm--><style>html[data-theme=dark]"
    if style not in html_text:
        raise SystemExit("style anchor missing")
    html_text = html_text.replace(style, CSS + "</style><!--thm--><style>html[data-theme=dark]", 1)
    html_text = html_text.replace('<span data-x="ch">69</span>', '<span data-x="ch">74</span>', 1)
    return html_text


def patch_js(html_text):
    a = "var W=DATA.W, CH=DATA.CH, CT=DATA.CT, LS=window.localStorage;"
    b = (
        "var W=DATA.W, CH=DATA.CH, CT=DATA.CT, LS=window.localStorage;"
        "if(window.WEEK&&WEEK.W){W=Object.assign({},DATA.W,WEEK.W);CH=Object.assign({},DATA.CH,WEEK.CH);CT=Object.assign({},DATA.CT,WEEK.CT);}"
    )
    if b not in html_text:
        if a not in html_text:
            raise SystemExit("W assign anchor missing")
        html_text = html_text.replace(a, b, 1)
    row_old = (
        """'<div class="row"><button class="pw'+(ACC==='us'?' cur':'')+'" data-i="'+i+'" data-acc="us">🇺🇸 美式</button><button class="pw'+(ACC==='uk'?' cur':'')+'" data-i="'+i+'" data-acc="uk">🇬🇧 英式</button>'+(all.length>1?'<button data-a="next">下一处 ('+(k+1)+'/'+all.length+')</button>':'')+"""
    )
    row_new = (
        """'<div class="row">'+(w.na?'<span class="meta">暂无音频</span>':'<button class="pw'+(ACC==='us'?' cur':'')+'" data-i="'+i+'" data-acc="us">🇺🇸 美式</button><button class="pw'+(ACC==='uk'?' cur':'')+'" data-i="'+i+'" data-acc="uk">🇬🇧 英式</button>')+(all.length>1?'<button data-a="next">下一处 ('+(k+1)+'/'+all.length+')</button>':'')+"""
    )
    if row_new not in html_text:
        if row_old not in html_text:
            raise SystemExit("pop row anchor missing")
        html_text = html_text.replace(row_old, row_new, 1)
    say_old = "var b=e.target.closest('.say');if(b){var p=b.closest('.para');if(b.classList.contains('on')){stop();return}playParas([p]);return}\n  var a=e.target.closest('.sayall');if(a){playParas($$('.para',a.closest('.chap')));return}"
    say_new = "var b=e.target.closest('.say');if(b){if(b.closest('.w11')){toast('本章暂无音频');return}var p=b.closest('.para');if(b.classList.contains('on')){stop();return}playParas([p]);return}\n  var a=e.target.closest('.sayall');if(a){if(a.closest('.w11')){toast('本章暂无音频');return}playParas($$('.para',a.closest('.chap')));return}"
    if say_new not in html_text:
        if say_old not in html_text:
            raise SystemExit("say anchor missing")
        html_text = html_text.replace(say_old, say_new, 1)
    miss_old = "if(!u){fallbackSpeak(paraText(p),next);return}"
    miss_new = "if(!u){if(p.closest&&p.closest('.w11')){toast('本章暂无音频');queue=[];clearReading();return}fallbackSpeak(paraText(p),next);return}"
    if miss_new not in html_text:
        if miss_old not in html_text:
            raise SystemExit("fallback anchor missing")
        html_text = html_text.replace(miss_old, miss_new, 1)
    # header: chapter count includes the side story; continue-reading can name chapters that are not in the main CT map
    ch_old = "setX('ch',chs.length);setX('w',NWD);"
    ch_new = "setX('ch',$$('section.chap').length||chs.length);setX('w',NWD);"
    if ch_new not in html_text:
        if ch_old not in html_text:
            raise SystemExit("chapter count anchor missing")
        html_text = html_text.replace(ch_old, ch_new, 1)
    last_old = "function lastRec(){var L=nav()&&nav().last?nav().last():ls('wsx-last');return L&&CT[L.c]?L:null}"
    last_new = "function chapZh(n){if(CT[n])return CT[n];var el=document.getElementById('c'+n),hs=el&&el.querySelector('h2 small');return hs?hs.textContent:('第 '+n+' 章')}function lastRec(){var L=nav()&&nav().last?nav().last():ls('wsx-last');if(!L)return null;if(CT[L.c]||document.getElementById('c'+L.c))return L;return null}"
    if "function chapZh(" not in html_text:
        if last_old not in html_text:
            raise SystemExit("lastRec anchor missing")
        html_text = html_text.replace(last_old, last_new, 1)
    # Deep links are resolved before chapter-end nav is inserted, so #c54 and later
    # land short of the real heading. Re-apply the hash once those nodes exist.
    boot_old = "onScroll();paint();\nwindow.addEventListener('hashchange'"
    boot_new = "onScroll();paint();\nvar boot=/^#(?:c(\\d+)|w1102)$/.exec(location.hash);if(boot){if(boot[1]&&idx[+boot[1]]!=null)go(+boot[1]);else if(!boot[1]){var wel=document.getElementById('w1102');if(wel){var wy=wel.getBoundingClientRect().top+window.pageYOffset-stickyH();try{window.scrollTo({top:Math.max(0,wy),left:0,behavior:'instant'})}catch(e){window.scrollTo(0,Math.max(0,wy))}}}}\nwindow.addEventListener('hashchange'"
    if boot_new not in html_text:
        if boot_old not in html_text:
            raise SystemExit("hash boot anchor missing")
        html_text = html_text.replace(boot_old, boot_new, 1)
    title_old = "$('#contT').textContent='继续阅读 · 第 '+L.c+' 章《'+CT[L.c]+'》';"
    title_new = "$('#contT').textContent='继续阅读 · 第 '+L.c+' 章《'+chapZh(L.c)+'》';"
    if title_new not in html_text:
        if title_old not in html_text:
            raise SystemExit("cont title anchor missing")
        html_text = html_text.replace(title_old, title_new, 1)
    return html_text


def main():
    W, CH, CT, body = build()
    # drop empty notes so the card does not render a blank note line
    for rec in W.values():
        if not rec.get("g"):
            rec.pop("g", None)
        rec.pop("sf", None)
    week = {"W": W, "CH": CH, "CT": CT}
    raw = "var WEEK=" + json.dumps(week, ensure_ascii=False, separators=(",", ":")) + ";\n"
    rel = "data/week-1102.js"
    path = os.path.join(SITE, rel)
    open(path, "w", encoding="utf-8").write(raw)
    ver = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    page = open(os.path.join(SITE, "stories.html"), encoding="utf-8").read()
    page = patch(page, body)
    page = patch_js(page)
    src = '<script src="data/words.js?v=784b9883"></script>'
    if src not in page:
        raise SystemExit("words.js src missing")
    page = page.replace(src, src + '<script src="data/week-1102.js?v=%s"></script>' % ver, 1)
    open(os.path.join(SITE, "stories.html"), "w", encoding="utf-8").write(page)
    print("cards", len(W), "chapters", list(CH), "week.js", ver, "bytes", len(raw))


if __name__ == "__main__":
    main()
