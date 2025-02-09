from datetime import datetime, time
from typing import List, Dict
from app.utils.logger import logger
from .patrol_config import PatrolRoute, PatrolSchedule, PATROL_ROUTES, PATROL_SCHEDULES

class PatrolAnalyzer:
    def __init__(self):
        self.patrol_records: Dict[str, List[datetime]] = {}  # 记录每个巡逻点的访问时间
        
    def is_patrol_time(self) -> bool:
        """检查当前是否在巡逻时间内"""
        current_time = datetime.now().time()
        for schedule in PATROL_SCHEDULES:
            if schedule.start_time <= current_time <= schedule.end_time:
                return True
        return False

    def analyze_patrol_route(self, guard_id: str, visited_points: List[str], 
                           route: PatrolRoute) -> Dict:
        """分析巡逻路线完成情况"""
        expected_points = set(point.point_id for point in route.points)
        visited_points_set = set(visited_points)
        
        missing_points = expected_points - visited_points_set
        completion_rate = len(visited_points_set) / len(expected_points) * 100

        return {
            'guard_id': guard_id,
            'route_id': route.route_id,
            'completion_rate': completion_rate,
            'missing_points': list(missing_points),
            'timestamp': datetime.now()
        }

    def check_patrol_interval(self, route_id: str) -> bool:
        """检查巡逻间隔是否符合要求"""
        if route_id not in self.patrol_records:
            return True

        last_patrol = self.patrol_records[route_id][-1]
        current_time = datetime.now()
        
        for schedule in PATROL_SCHEDULES:
            time_diff = (current_time - last_patrol).total_seconds() / 60
            if time_diff < schedule.interval:
                return False
        return True

    def record_patrol(self, guard_id: str, point_id: str):
        """记录巡逻点位打卡"""
        current_time = datetime.now()
        if point_id not in self.patrol_records:
            self.patrol_records[point_id] = []
        
        self.patrol_records[point_id].append(current_time)
        logger.info(f"保安 {guard_id} 在 {current_time} 到达巡逻点 {point_id}")

    def generate_patrol_report(self, start_time: datetime, end_time: datetime) -> Dict:
        """生成巡逻报告"""
        report = {
            'period': {
                'start': start_time,
                'end': end_time
            },
            'routes_completion': [],
            'abnormal_events': []
        }

        # 分析每条路线的完成情况
        for route in PATROL_ROUTES:
            route_records = self._analyze_route_completion(route, start_time, end_time)
            report['routes_completion'].append(route_records)

        return report

    def _analyze_route_completion(self, route: PatrolRoute, 
                                start_time: datetime, 
                                end_time: datetime) -> Dict:
        """分析特定路线在给定时间段内的完成情况"""
        # TODO: 实现路线完成情况分析
        pass 