import json

import httpx
import ratelimit
import tenacity

from lokbot.exceptions import DuplicatedException, ExceedLimitPacketException, NoAuthException, NeedCaptchaException, \
    OtherException
from lokbot import logger

API_BASE_URL = 'https://api-lok-live.leagueofkingdoms.com/api/'


class LokBotApi:
    def __init__(self, access_token):
        self.opener = httpx.Client(
            headers={
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Origin': 'https://play.leagueofkingdoms.com',
                'Referer': 'https://play.leagueofkingdoms.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0',
                'x-access-token': access_token
            },
            http2=True,
            base_url=API_BASE_URL
        )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_exception_type(httpx.HTTPError),  # general http error
        reraise=True
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),  # client-side rate limiter
    )
    @tenacity.retry(
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_exception_type(DuplicatedException),  # server-side rate limiter(wait ~2s)
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(3600),
        retry=tenacity.retry_if_exception_type(ExceedLimitPacketException),  # server-side rate limiter(wait 1h)
    )
    @ratelimit.limits(calls=1, period=2)
    def post(self, url, json_data=None):
        if json_data is None:
            json_data = {}

        response = self.opener.post(url, data={'json': json.dumps(json_data)})

        json_response = response.json()

        logger.debug(json.dumps({
            'url': url,
            'data': json_data,
            'res': json_response,
            'elapsed': response.elapsed.total_seconds()
        }))

        if json_response.get('result'):
            return json_response

        err = json_response.get('err')
        code = err.get('code')

        if code == 'no_auth':
            raise NoAuthException()

        if code == 'need_captcha':
            raise NeedCaptchaException()

        if code == 'duplicated':
            raise DuplicatedException()

        if code == 'exceed_limit_packet':
            raise ExceedLimitPacketException()

        raise OtherException(code)

    def auth_captcha(self):
        return self.opener.get('auth/captcha')

    def auth_captcha_confirm(self, value):
        return self.post('auth/captcha/confirm', {'value': value})

    def alliance_research_list(self):
        return self.post('alliance/research/list')

    def alliance_research_donate_all(self, code):
        return self.post('alliance/research/donateAll', {'code': code})

    def quest_list(self):
        """
        获取任务列表
        :return:
        """
        return self.post('quest/list')

    def quest_list_daily(self):
        """
        获取日常任务列表
        :return:
        """
        return self.post('quest/list/daily')

    def quest_claim(self, quest):
        """
        领取任务奖励
        :param quest:
        :return:
        """
        return self.post('quest/claim', {'questId': quest.get('_id'), 'code': quest.get('code')})

    def quest_claim_daily(self, quest):
        """
        领取日常任务奖励
        :param quest:
        :return:
        """
        return self.post('quest/claim/daily', {'questId': quest.get('_id'), 'code': quest.get('code')})

    def quest_claim_daily_level(self, reward):
        """
        领取日常任务上方进度条奖励
        :param reward:
        :return:
        """
        return self.post('quest/claim/daily/level', {'level': reward.get('level')})

    def kingdom_enter(self):
        """
        获取基础信息
        :return:
        """
        return self.post('kingdom/enter')

    def kingdom_task_all(self):
        """
        获取当前任务执行状态(左侧建筑x2/招募/研究)
        :return:
        """
        return self.post('kingdom/task/all')

    def kingdom_task_claim(self, position):
        """
        领取任务奖励
        :return:
        """
        return self.post('kingdom/task/claim', {'position': position})

    def kingdom_tutorial_finish(self, code):
        """
        完成教程
        :return:
        """
        return self.post('kingdom/tutorial/finish', {'code': code})

    def kingdom_academy_research_list(self):
        """
        获取研究列表
        :return:
        """
        return self.post('kingdom/arcademy/research/list')

    def kingdom_hospital_recover(self):
        """
        医院恢复
        :return:
        """
        return self.post('kingdom/hospital/recover')

    def kingdom_resource_harvest(self, position):
        """
        收获资源
        :param position:
        :return:
        """
        return self.post('kingdom/resource/harvest', {'position': position})

    def kingdom_building_upgrade(self, building, instant=0):
        """
        建筑升级
        :param building:
        :param instant:
        :return:
        """
        return self.post('kingdom/building/upgrade', {
            'position': building.get('position'),
            'level': building.get('level'),
            'instant': instant
        })

    def kingdom_academy_research(self, research, instant=0):
        """
        学院研究升级
        :param research:
        :param instant:
        :return:
        """
        return self.post('kingdom/arcademy/research', {
            'researchCode': research.get('code'),
            'instant': instant
        })

    def kingdom_vip_info(self):
        """
        获取VIP信息
        :return:
        """
        return self.post('kingdom/vip/info')

    def kingdom_vip_claim(self):
        """
        领取VIP奖励
        daily
        :return:
        """
        return self.post('kingdom/vip/claim')

    def kingdom_world_change(self, world_id):
        """
        切换世界
        :param world_id:
        :return:
        """
        return self.post('kingdom/world/change', {'worldId': world_id})

    def alliance_help_all(self):
        """
        帮助全部
        :return:
        """
        return self.post('alliance/help/all')

    def item_list(self):
        """
        获取道具列表
        :return:
        """
        return self.post('item/list')

    def item_use(self, code, amount=1):
        """
        使用道具
        :param code:
        :param amount:
        :return:
        """
        return self.post('item/use', {'code': code, 'amount': amount})

    def item_free_chest(self, _type=0):
        """
        领取免费宝箱
        :type _type: int 0: silver 1: gold
        :return:
        """
        return self.post('item/freechest', {'type': _type})

    def event_roulette_spin(self):
        """
        转轮抽奖
        daily
        :return:
        """
        return self.post('event/roulette/spin')
