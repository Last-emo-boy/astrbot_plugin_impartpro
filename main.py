from astrbot.api.all import *
import os
import json
import random
import datetime

@register("impartpro", "w33d", "牛牛小游戏", "1.0.0", "https://github.com/Last-emo-boy/astrbot_plugin_impartpro")
class ImpartProPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        # 存储文件位于当前文件同级目录
        self.storage_file = os.path.join(os.path.dirname(__file__), "impartpro_data.json")
        self.data = self.load_data()

    # ---------------- JSON 数据存储辅助方法 ----------------
    def load_data(self) -> dict:
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    else:
                        return {}
            except Exception:
                return {}
        else:
            return {}

    def save_data(self):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_record(self, userid: str):
        return self.data.get(userid)

    def get_all_records(self):
        return list(self.data.values())

    def update_record(self, userid: str, update: dict):
        record = self.data.get(userid, {})
        record.update(update)
        self.data[userid] = record
        self.save_data()

    def create_record(self, userid: str, record: dict):
        self.data[userid] = record
        self.save_data()

    async def update_channel_id(self, user_id: str, new_channel_id: str) -> list:
        record = self.get_record(user_id)
        if not record:
            return [new_channel_id]
        current = record.get("channelId", [])
        if new_channel_id not in current:
            current.append(new_channel_id)
            self.update_record(user_id, {"channelId": current})
        return current

    def logger_info(self, message: str):
        if self.config.get("loggerinfo"):
            self.context.logger.info(message)

    async def update_user_currency(self, uid: str, amount: float, currency: str = None) -> str:
        try:
            if currency is None:
                currency = self.config.get("currency", "default")
            numeric_uid = int(uid)
            if amount > 0:
                await self.context.monetary.gain(numeric_uid, amount, currency)
                self.logger_info(f"为用户 {uid} 增加了 {amount} {currency}")
            elif amount < 0:
                await self.context.monetary.cost(numeric_uid, -amount, currency)
                self.logger_info(f"为用户 {uid} 减少了 {-amount} {currency}")
            return f"用户 {uid} 成功更新了 {abs(amount)} {currency}"
        except Exception as e:
            self.context.logger.error(f"更新用户 {uid} 的货币时出错: {e}")
            return f"更新用户 {uid} 的货币时出现问题。"

    async def get_user_currency(self, uid: str, currency: str = None) -> float:
        try:
            if currency is None:
                currency = self.config.get("currency", "default")
            numeric_uid = int(uid)
            # 此处仅作示例，直接调用 monetary 模块查询
            records = await self.context.monetary.get(numeric_uid, currency)
            if records:
                return records.get("value", 0)
            return 0
        except Exception as e:
            self.context.logger.error(f"获取用户 {uid} 的货币时出错: {e}")
            return 0

    async def update_id_by_user_id(self, user_id: str, platform: str) -> str:
        # 此处直接返回 user_id 作示例
        return user_id

    # ---------------- 注册命令组 ----------------
    @command_group("impartpro")
    def impartpro(self):
        pass

    # 子命令：注入
    @impartpro.command("注入")
    async def inject(self, event: AstrMessageEvent, user: str = None):
        '''注入群友'''
        current_date = datetime.datetime.now()
        formatted_date = str(current_date.day)
        milliliter_range = self.config.get("milliliter_range", [10, 100])
        random_ml = round(self.random_length(milliliter_range[0], milliliter_range[1]), 2)

        target_user_id = None
        target_username = None

        if user:
            # 要求用户以 @ 开头
            if user.startswith("@"):
                target_user_id = user[1:]
                target_username = target_user_id
                if target_user_id == event.get_sender_id():
                    yield event.plain_result("不允许自己注入自己哦~ 换一个用户吧")
                    return
            else:
                yield event.plain_result("输入的用户格式不正确，请使用 @用户 格式。")
                return
        else:
            # 从所有记录中随机选择一个符合条件的用户
            records = self.get_all_records()
            drawing_scope = self.config.get("randomdrawing", "1")
            if drawing_scope == "1":
                filtered = [r for r in records if event.session_id in r.get("channelId", [])
                            and not r.get("userid", "").startswith("channel_")
                            and r.get("userid") != event.get_sender_id()]
            elif drawing_scope == "2":
                filtered = [r for r in records if not r.get("userid", "").startswith("channel_")
                            and r.get("userid") != event.get_sender_id()]
            else:
                filtered = []
            if not filtered:
                yield event.plain_result("未找到符合条件的用户。")
                return
            target_record = random.choice(filtered)
            target_user_id = target_record.get("userid")
            target_username = target_record.get("username") or f"用户 {target_user_id}"

        if not self.get_record(target_user_id):
            yield event.plain_result(f"未找到用户 {target_user_id} 的记录。请先 开导 @{target_user_id}")
            return

        # 仅保留当天数据
        target_record = self.get_record(target_user_id)
        inject_data = {}
        if target_record.get("injectml"):
            parts = target_record["injectml"].split("-")
            if len(parts) == 2 and parts[0] == formatted_date:
                try:
                    inject_data[formatted_date] = float(parts[1])
                except:
                    inject_data[formatted_date] = 0
            else:
                inject_data[formatted_date] = 0
        else:
            inject_data[formatted_date] = 0

        inject_data[formatted_date] += random_ml
        updated_inject = f"{formatted_date}-{inject_data[formatted_date]:.2f}"
        self.update_record(target_user_id, {"injectml": updated_inject})
        total_ml = f"{inject_data[formatted_date]:.2f}"
        image_link = f"http://q.qlogo.cn/headimg_dl?dst_uin={target_user_id}&spec=640"
        message = (f"现在咱将随机抽取一位幸运群友送给 {event.get_sender_name()}！\n"
                   f"好诶！{event.get_sender_name()} 给 {target_username} 注入了{random_ml}毫升的脱氧核糖核酸，\n"
                   f"{target_username}当日的总注入量为{total_ml}毫升")
        yield event.plain_result(message + f"\n图片: {image_link}")

    # 子命令：保养
    @impartpro.command("保养")
    async def maintain(self, event: AstrMessageEvent):
        '''通过花费货币来增加牛牛的长度'''
        user_id = event.get_sender_id()
        record = self.get_record(user_id)
        if not record:
            yield event.plain_result("你还没有数据，请先进行初始化。")
            return
        user_currency = await self.get_user_currency(user_id)
        cost_per_unit = self.config.get("maintenanceCostPerUnit", 0.1)
        max_length = int(user_currency / (1 / cost_per_unit))
        if max_length <= 0:
            yield event.plain_result("你的货币不足以进行保养。")
            return
        yield event.plain_result(f"你可以购买的最大长度为 {max_length} cm，请在后台配置你想购买的长度。")

    # 子命令：开导
    @impartpro.command("开导")
    async def coach(self, event: AstrMessageEvent, user: str = None):
        '''让牛牛成长！'''
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        now = datetime.datetime.now()
        if user:
            if user.startswith("@"):
                target = user[1:]
                if target == user_id:
                    yield event.plain_result("不可用的用户！请换一个用户吧~")
                    return
                user_id = target
                username = target
            else:
                yield event.plain_result("不可用的用户！请检查输入")
                return
        else:
            # 更新自己在记录中的用户名
            self.update_record(user_id, {"username": username})

        record = self.get_record(user_id)
        if not record:
            default_length = self.random_length(*self.config.get("defaultLength", [18, 45]))
            growth_factor = random.random()
            record = {
                "userid": user_id,
                "username": username,
                "channelId": [event.session_id],
                "length": default_length,
                "injectml": "0-0",
                "growthFactor": growth_factor,
                "lastGrowthTime": now.isoformat(),
                "lastDuelTime": now.isoformat(),
                "locked": False
            }
            self.create_record(user_id, record)
            yield event.plain_result(f"@{user_id} 自动初始化成功！你的牛牛初始长度为 {default_length:.2f} cm，生长系数为 {growth_factor:.2f}")
            return

        try:
            last_growth = datetime.datetime.fromisoformat(record.get("lastGrowthTime"))
        except Exception:
            yield event.plain_result("用户数据有误，无法解析最后锻炼时间。")
            return
        cooldown = self.config.get("exerciseCooldownTime", 5)
        if (now - last_growth).total_seconds() < cooldown:
            remaining = int(cooldown - (now - last_growth).total_seconds())
            yield event.plain_result(f"@{user_id} 处于冷却中，无法进行锻炼。冷却还剩 {remaining} 秒。")
            return

        original_length = record.get("length", 0)
        success_rate = 50
        for item in self.config.get("exerciseRate", []):
            if original_length >= item.get("minlength", 0) and original_length < item.get("maxlength", 100):
                success_rate = item.get("rate", 50)
                break
        is_success = random.random() * 100 < success_rate
        if is_success:
            base, variance = self.config.get("exerciseWinGrowthRange", [10, 45])
            expected = self.random_length(base, variance)
            growth_change = expected * (1 + record.get("growthFactor", 0))
        else:
            base, variance = self.config.get("exerciseLossReductionRange", [12, 45])
            expected = self.random_length(base, variance)
            growth_change = -expected

        enhanced = original_length + growth_change
        record["length"] = enhanced
        record["lastGrowthTime"] = now.isoformat()

        self.logger_info(f"用户ID: {user_id}")
        self.logger_info(f"原有长度: {original_length:.2f} cm")
        self.logger_info(f"实际应用的成长值: {growth_change:.2f} cm")
        self.logger_info(f"牛牛增长因数: {record.get('growthFactor', 0):.2f}")
        self.logger_info(f"计算结果: {original_length:.2f} + {growth_change:.2f} = {enhanced:.2f} cm")
        self.logger_info(f"锻炼结果: {'成功' if is_success else '失败'}")

        # 更新记录
        self.update_record(user_id, {"length": enhanced, "lastGrowthTime": record["lastGrowthTime"],
                                       "channelId": await self.update_channel_id(user_id, event.session_id)})
        yield event.plain_result(f"@{user_id} 锻炼{'成功' if is_success else '失败'}！牛牛强化后长度为 {enhanced:.2f} cm。")

    # 子命令：牛牛决斗
    @impartpro.command("牛牛决斗")
    async def duel(self, event: AstrMessageEvent, user: str):
        '''决斗牛牛！'''
        attacker_id = event.get_sender_id()
        now = datetime.datetime.now()
        if user:
            if user.startswith("@"):
                target = user[1:]
                if target == attacker_id:
                    yield event.plain_result("不可用的用户！请换一个用户吧~")
                    return
                defender_id = target
            else:
                yield event.plain_result("不可用的用户！请检查输入")
                return
        else:
            yield event.plain_result("请指定一个决斗用户！\n示例：决斗 @用户")
            return

        attacker_record = self.get_record(attacker_id)
        if not attacker_record:
            yield event.plain_result("你还没有数据，请先进行初始化。")
            return
        defender_record = self.get_record(defender_id)
        if not defender_record:
            yield event.plain_result("目标用户还没有数据，无法进行决斗。")
            return

        try:
            last_attacker = datetime.datetime.fromisoformat(attacker_record.get("lastDuelTime"))
            last_defender = datetime.datetime.fromisoformat(defender_record.get("lastDuelTime"))
        except Exception:
            yield event.plain_result("用户数据有误，无法解析最后决斗时间。")
            return

        cooldown = self.config.get("duelCooldownTime", 15)
        if (now - last_attacker).total_seconds() < cooldown or (now - last_defender).total_seconds() < cooldown:
            remaining = max(cooldown - (now - last_attacker).total_seconds(), cooldown - (now - last_defender).total_seconds())
            yield event.plain_result(f"你或目标用户处于冷却中，无法进行决斗。\n冷却还剩 {int(remaining)} 秒。")
            return

        length_diff = attacker_record.get("length", 0) - defender_record.get("length", 0)
        base_rate = 50
        for item in self.config.get("duelWinRateFactor", []):
            if abs(length_diff) >= item.get("minlength", 0) and abs(length_diff) < item.get("maxlength", 100):
                base_rate = item.get("rate", 50)
                break
        attacker_is_longer = attacker_record.get("length", 0) > defender_record.get("length", 0)
        factor2 = self.config.get("duelWinRateFactor2", -10)
        attacker_win_rate = base_rate - factor2 if attacker_is_longer else base_rate + factor2
        final_rate = max(0, min(100, attacker_win_rate))
        if random.random() * 100 < final_rate:
            base_growth, growth_var = self.config.get("duelWinGrowthRange", [10, 50])
            growth_change = self.random_length(base_growth, growth_var)
            base_reduction, reduction_var = self.config.get("duelLossReductionRange", [15, 50])
            reduction_change = self.random_length(base_reduction, reduction_var)
            attacker_record["length"] += growth_change
            defender_record["length"] -= reduction_change
            duel_loss_currency = self.config.get("duelLossCurrency", 80)
            currency_gain = reduction_change * (duel_loss_currency / 100)
            await self.update_user_currency(defender_id, currency_gain)
            result_text = "胜利"
        else:
            base_growth, growth_var = self.config.get("duelWinGrowthRange", [10, 50])
            growth_change = self.random_length(base_growth, growth_var)
            base_reduction, reduction_var = self.config.get("duelLossReductionRange", [15, 50])
            reduction_change = self.random_length(base_reduction, reduction_var)
            defender_record["length"] += growth_change
            attacker_record["length"] -= reduction_change
            duel_loss_currency = self.config.get("duelLossCurrency", 80)
            currency_gain = reduction_change * (duel_loss_currency / 100)
            await self.update_user_currency(attacker_id, currency_gain)
            result_text = "失败"

        attacker_record["lastDuelTime"] = now.isoformat()
        defender_record["lastDuelTime"] = now.isoformat()

        self.update_record(attacker_id, {"length": attacker_record["length"],
                                          "lastDuelTime": attacker_record["lastDuelTime"],
                                          "channelId": await self.update_channel_id(attacker_id, event.session_id)})
        self.update_record(defender_id, {"length": defender_record["length"],
                                          "lastDuelTime": defender_record["lastDuelTime"],
                                          "channelId": await self.update_channel_id(defender_id, event.session_id)})
        self.logger_info(f"攻击者ID: {attacker_id}, 胜率: {final_rate:.2f}%")
        self.logger_info(f"防御者ID: {defender_id}, 胜率: {(100 - final_rate):.2f}%")
        message = (f"@{attacker_id} 决斗{result_text}！\n"
                   f"@{attacker_id} {'增加' if result_text=='胜利' else '减少'}了 {growth_change:.2f} cm，\n"
                   f"@{defender_id} {'减少' if result_text=='胜利' else '增加'}了 {reduction_change:.2f} cm。\n"
                   f"战败方获得了 {currency_gain:.2f} 点经验（货币）。")
        yield event.plain_result(message)

    # 子命令：重开牛牛
    @impartpro.command("重开牛牛")
    async def reset(self, event: AstrMessageEvent):
        '''重开一个牛牛~'''
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        initial_length = self.random_length(*self.config.get("defaultLength", [18, 45]))
        growth_factor = random.random()
        now_iso = datetime.datetime.now().isoformat()
        record = self.get_record(user_id)
        if record:
            self.update_record(user_id, {"length": initial_length,
                                          "growthFactor": growth_factor,
                                          "lastDuelTime": now_iso,
                                          "channelId": await self.update_channel_id(user_id, event.session_id)})
            yield event.plain_result(f"牛牛重置成功，当前长度为 {initial_length:.2f} cm，成长系数为 {growth_factor:.2f}。")
        else:
            record = {
                "userid": user_id,
                "username": username,
                "channelId": [event.session_id],
                "length": initial_length,
                "injectml": "0-0",
                "growthFactor": growth_factor,
                "lastGrowthTime": now_iso,
                "lastDuelTime": now_iso,
                "locked": False
            }
            self.create_record(user_id, record)
            yield event.plain_result(f"牛牛初始化成功，当前长度为 {initial_length:.2f} cm，成长系数为 {growth_factor:.2f}。")

    # 子命令：注入排行榜
    @impartpro.command("注入排行榜")
    async def inject_leaderboard(self, event: AstrMessageEvent):
        '''查看注入排行榜'''
        num = self.config.get("leaderboardPeopleNumber", 10)
        enable_all = self.config.get("enableAllChannel", False)
        day = str(datetime.datetime.now().day)
        records = self.get_all_records()
        if enable_all:
            filtered = [r for r in records if r.get("username") != "频道"]
        else:
            filtered = [r for r in records if event.session_id in r.get("channelId", []) and r.get("username") != "频道"]
        valid = []
        for r in filtered:
            injectml = r.get("injectml")
            if not injectml:
                continue
            parts = injectml.split("-")
            if len(parts) == 2 and parts[0] == day:
                try:
                    valid.append({"username": r.get("username") or f"用户 {r.get('userid')}",
                                  "milliliter": float(parts[1])})
                except:
                    continue
        if not valid:
            yield event.plain_result("当前没有可用的注入排行榜数据。")
            return
        valid.sort(key=lambda x: x["milliliter"], reverse=True)
        top = valid[:num]
        rank_data = [{"order": i+1, "username": rec["username"], "milliliter": f"{rec['milliliter']:.2f}"}
                     for i, rec in enumerate(top)]
        leaderboard_text = "\n".join([f"{rec['order']}. {rec['username']}: {rec['milliliter']} mL" for rec in rank_data])
        yield event.plain_result("今日注入排行榜：\n" + leaderboard_text)

    # 子命令：牛牛排行榜
    @impartpro.command("牛牛排行榜")
    async def length_leaderboard(self, event: AstrMessageEvent):
        '''查看牛牛排行榜'''
        num = self.config.get("leaderboardPeopleNumber", 10)
        enable_all = self.config.get("enableAllChannel", False)
        records = self.get_all_records()
        if enable_all:
            filtered = records
        else:
            filtered = [r for r in records if event.session_id in r.get("channelId", [])]
        valid = [r for r in filtered if r.get("username") != "频道"]
        if not valid:
            yield event.plain_result("当前没有可用的排行榜数据。")
            return
        valid.sort(key=lambda r: r.get("length", 0), reverse=True)
        top = valid[:num]
        rank_data = [{"order": i+1, "username": r.get("username"), "length": f"{r.get('length', 0):.2f}"}
                     for i, r in enumerate(top)]
        leaderboard_text = "\n".join([f"{rec['order']}. {rec['username']}: {rec['length']} cm" for rec in rank_data])
        yield event.plain_result("牛牛排行榜：\n" + leaderboard_text)

    # 子命令：看看牛牛
    @impartpro.command("看看牛牛")
    async def show_length(self, event: AstrMessageEvent, user: str = None):
        '''查看牛牛'''
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        if user:
            if user.startswith("@"):
                user_id = user[1:]
                username = user_id
            else:
                yield event.plain_result("不可用的用户！请检查输入")
                return
        record = self.get_record(user_id)
        if not record:
            yield event.plain_result(f"暂时没有@{user_id} 的记录。快输入【重开牛牛】进行初始化吧")
            return
        balance = await self.get_user_currency(user_id)
        yield event.plain_result(f"@{user_id} 的牛牛长度为 {record.get('length', 0):.2f} cm，生长系数为 {record.get('growthFactor', 0):.2f}。\n剩余点数为：{balance:.2f}")

    # 子命令：锁牛牛
    @impartpro.command("锁牛牛")
    async def lock(self, event: AstrMessageEvent, user: str = None):
        '''开启/禁止牛牛大作战'''
        channel_id = event.session_id
        if user:
            if user.startswith("@"):
                target_user = user[1:]
            else:
                yield event.plain_result("不可用的用户！请检查输入")
                return
            record = self.get_record(target_user)
            if not record:
                rec = {"userid": target_user, "username": target_user, "channelId": [channel_id], "locked": True}
                self.create_record(target_user, rec)
                yield event.plain_result(f"用户 {target_user} 已被禁止触发牛牛大作战。")
            else:
                current = record.get("locked", False)
                new_status = not current
                self.update_record(target_user, {"locked": new_status})
                yield event.plain_result(f"用户 {target_user} 已{'被禁止' if new_status else '可以'}触发牛牛大作战。")
        else:
            special = f"channel_{channel_id}"
            record = self.get_record(special)
            if not record:
                rec = {"userid": special, "username": "频道", "channelId": [channel_id], "locked": True}
                self.create_record(special, rec)
                yield event.plain_result("牛牛大作战已在本频道被禁止。")
            else:
                current = record.get("locked", False)
                new_status = not current
                self.update_record(special, {"locked": new_status})
                yield event.plain_result(f"牛牛大作战已在本频道{'被禁止' if new_status else '开启'}。")

    # ---------------- 辅助函数 ----------------
    def random_length(self, base: float, variance: float) -> float:
        """计算随机长度：base ± (base * variance/100)"""
        min_val = base * (1 - variance / 100)
        max_val = base * (1 + variance / 100)
        return random.uniform(min_val, max_val)
