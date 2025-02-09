import argparse
from datetime import datetime, timedelta
from app.mall_monitor.security_patrol.patrol_point_manager import PatrolPointManager

def print_records(records: List[Dict]):
    """打印巡逻记录"""
    if not records:
        print("\n未找到巡逻记录")
        return
        
    print("\n巡逻记录:")
    print("-" * 80)
    print(f"{'时间':<20} {'保安':<10} {'摄像头':<15} {'点位':<15}")
    print("-" * 80)
    
    for record in records:
        print(f"{record['arrival_time'].strftime('%Y-%m-%d %H:%M:%S'):<20} "
              f"{record['guard_name']:<10} "
              f"{record['camera_name']:<15} "
              f"{record['point_name']:<15}")

def main():
    parser = argparse.ArgumentParser(description='巡逻记录查询工具')
    parser.add_argument('--start', help='开始时间 (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', help='结束时间 (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--guard', help='保安ID')
    parser.add_argument('--point', type=int, help='点位ID')
    args = parser.parse_args()
    
    try:
        manager = PatrolPointManager()
        
        # 解析时间
        start_time = None
        if args.start:
            start_time = datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        
        end_time = None
        if args.end:
            end_time = datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
        
        # 查询记录
        records = manager.get_patrol_records(
            start_time=start_time,
            end_time=end_time,
            guard_id=args.guard,
            point_id=args.point
        )
        
        # 打印结果
        print_records(records)
        
    except Exception as e:
        print(f"\n查询失败: {str(e)}")

if __name__ == "__main__":
    main() 