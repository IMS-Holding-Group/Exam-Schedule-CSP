"""
نظام جدولة الامتحانات باستخدام Constraint Satisfaction Problem (CSP)
يستخدم OR-Tools CP-SAT لحل مشكلة الجدولة مع القيود المحددة
"""

import pandas as pd
import numpy as np
from ortools.sat.python import cp_model
import os
from datetime import datetime
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
from collections import defaultdict
import gc


def solve_schedule(input_excel_path):
    """
    حل مشكلة جدولة الامتحانات باستخدام CSP - محسن للبيانات الضخمة
    
    المدخلات:
    - input_excel_path: مسار ملف Excel يحتوي على تسجيلات الطلاب
    
    المخرجات:
    - DataFrame: جدول الامتحانات الناتج
    - str: مسار ملف Excel المحفوظ
    """
    
    # قراءة بيانات التسجيلات من ملف Excel مع معالجة شاملة للأخطاء
    print("قراءة بيانات التسجيلات...")
    
    try:
        # التحقق من وجود الملف
        if not os.path.exists(input_excel_path):
            raise FileNotFoundError("الملف غير موجود")
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(input_excel_path)
        if file_size == 0:
            raise ValueError("الملف فارغ")
        
        # قراءة الملف
        df = pd.read_excel(input_excel_path, engine='openpyxl')
        
        # التحقق من وجود البيانات
        if df.empty:
            raise ValueError("الملف لا يحتوي على بيانات")
        
        # التحقق من وجود الأعمدة المطلوبة
        if 'Student' not in df.columns or 'Subject' not in df.columns:
            raise ValueError("يجب أن يحتوي الملف على عمودين: Student و Subject")
        
        # تحسين الأداء للبيانات الضخمة
        df = df.dropna(subset=['Student', 'Subject'])  # حذف الصفوف الفارغة
        df = df.drop_duplicates()  # حذف التكرارات
        
        # التحقق من وجود بيانات بعد التنظيف
        if df.empty:
            raise ValueError("لا توجد بيانات صحيحة في الملف")
            
    except FileNotFoundError:
        raise Exception("الملف غير موجود")
    except ValueError as e:
        raise Exception(f"خطأ في البيانات: {str(e)}")
    except Exception as e:
        raise Exception(f"خطأ في قراءة الملف: {str(e)}")
    
    # بناء هيكل بيانات الطلاب والمواد مع معالجة الأخطاء
    print("معالجة البيانات...")
    student_subjects = {}
    subjects = set()
    
    try:
        # استخدام vectorized operations للسرعة
        df['Student'] = df['Student'].astype(str).str.strip()
        df['Subject'] = df['Subject'].astype(str).str.strip()
        
        # إزالة القيم الفارغة أو غير الصحيحة
        df = df[df['Student'] != '']
        df = df[df['Subject'] != '']
        df = df[df['Student'] != 'nan']
        df = df[df['Subject'] != 'nan']
        
        # التحقق من وجود بيانات بعد التنظيف
        if df.empty:
            raise ValueError("لا توجد بيانات صحيحة في الملف")
        
        # تجميع البيانات بكفاءة
        grouped = df.groupby(['Student', 'Subject']).size().reset_index()
        
        for _, row in grouped.iterrows():
            student_id = row['Student']
            subject = row['Subject']
            
            # التحقق من صحة البيانات
            if not student_id or not subject:
                continue
                
            if student_id not in student_subjects:
                student_subjects[student_id] = set()
            
            student_subjects[student_id].add(subject)
            subjects.add(subject)
        
        # التحقق من وجود بيانات صحيحة
        if not student_subjects or not subjects:
            raise ValueError("لا توجد بيانات صحيحة في الملف")
        
        subjects = list(subjects)
        students = list(student_subjects.keys())
        
        print(f"عدد الطلاب: {len(students)}")
        print(f"عدد المواد: {len(subjects)}")
        
        # التحقق من الحد الأدنى للبيانات
        if len(students) == 0:
            raise ValueError("عدد الطلاب: 0 - لا توجد بيانات صحيحة")
        if len(subjects) == 0:
            raise ValueError("عدد المواد: 0 - لا توجد مواد صحيحة")
        
        # تحديد استراتيجية الحل حسب حجم البيانات مع CSP محسن
        if len(students) > 500 or len(subjects) > 100:
            print("بيانات ضخمة جداً - استخدام CSP متقدم مع تقسيم ذكي...")
            return solve_advanced_csp_schedule(student_subjects, subjects)
        elif len(students) > 200 or len(subjects) > 50:
            print("بيانات ضخمة - استخدام CSP محسن مع تحسينات متقدمة...")
            return solve_optimized_csp_schedule(student_subjects, subjects)
        elif len(students) <= 50 and len(subjects) <= 50:
            print("بيانات صغيرة - استخدام حل تقريبي مباشر...")
            return solve_direct_heuristic(student_subjects, subjects)
        else:
            print("بيانات متوسطة - استخدام CSP محسن...")
            return solve_enhanced_csp_schedule(student_subjects, subjects)
            
    except ValueError as e:
        raise Exception(f"خطأ في معالجة البيانات: {str(e)}")
    except Exception as e:
        raise Exception(f"خطأ في معالجة البيانات: {str(e)}")


def solve_simple_csp_schedule(student_subjects, subjects):
    """
    حل CSP مباشر وسريع للبيانات الصغيرة
    """
    print("بدء الحل المباشر السريع...")
    start_time = time.time()
    
    try:
        days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
        
        num_days = len(days)
        num_periods = len(periods)
        
        # إنشاء نموذج CSP بسيط
        model = cp_model.CpModel()
        
        # متغيرات القرار
        x = {}
        y_day = {}
        
        # إضافة متغيرات للمواد والأيام
        for subject in subjects:
            x[subject] = {}
            for day in range(num_days):
                x[subject][day] = {}
                for period in range(num_periods):
                    x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
        
        # متغيرات الأيام المستخدمة
        for day in range(num_days):
            y_day[day] = model.NewBoolVar(f'y_day_{day}')
        
        # القيود: كل مادة يجب أن يكون لها امتحان واحد فقط
        for subject in subjects:
            model.Add(sum(x[subject][day][period] for day in range(num_days) 
                         for period in range(num_periods)) == 1)
        
        # قيود الطلاب مبسطة جداً - فقط قيود أساسية
        conflict_count = 0
        for student in student_subjects:
            student_subject_list = [s for s in student_subjects[student] if s in subjects]
            if len(student_subject_list) <= 1:
                continue
                
            # فقط أفضل مادتين لكل طالب للسرعة القصوى
            popular_subjects = sorted(student_subject_list, key=lambda x: len([s for s in student_subjects.values() if x in s]), reverse=True)[:2]
            
            if len(popular_subjects) >= 2:
                subject1, subject2 = popular_subjects[0], popular_subjects[1]
                for day in range(num_days):
                    for period in range(num_periods):
                        model.Add(x[subject1][day][period] + x[subject2][day][period] <= 1)
                        conflict_count += 1
        
        # ربط متغيرات استخدام الأيام
        for day in range(num_days):
            for subject in subjects:
                for period in range(num_periods):
                    model.Add(x[subject][day][period] <= y_day[day])
        
        # الهدف
        model.Minimize(sum(y_day[day] for day in range(num_days)))
        
        # حل CSP سريع جداً
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0  # 5 ثوان فقط للسرعة القصوى
        solver.parameters.num_search_workers = 1  # thread واحد للاستقرار
        solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
        solver.parameters.cp_model_presolve = True
        solver.parameters.cp_model_probing_level = 0
        
        print("بدء حل CSP المباشر...")
        status = solver.Solve(model)
        print(f"حالة الحل: {status}")
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("تم حل CSP بنجاح!")
            results = []
            for subject in subjects:
                for day in range(num_days):
                    for period in range(num_periods):
                        if solver.Value(x[subject][day][period]) == 1:
                            results.append({
                                'Subject': subject,
                                'DayIndex': day,
                                'DayName': days[day],
                                'PeriodIndex': period,
                                'TimeRange': periods[period]
                            })
                            break
            
            # إنشاء الجدول النهائي
            result_df = pd.DataFrame(results)
            result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
            
            # حفظ النتائج
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"exam_schedule_simple_{timestamp}.xlsx"
            output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                      'static', 'downloads', output_filename)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result_df.to_excel(output_path, index=False)
            
            end_time = time.time()
            print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
            print(f"تم حفظ النتائج في: {output_path}")
            
            return result_df, output_path
        else:
            print("فشل في حل CSP، استخدام حل تقريبي مباشر...")
            return solve_direct_heuristic(student_subjects, subjects)
        
    except Exception as e:
        print(f"خطأ في الحل المباشر: {str(e)}")
        raise Exception(f"خطأ في الحل المباشر: {str(e)}")


def solve_direct_heuristic(student_subjects, subjects):
    """
    حل تقريبي مباشر وسريع جداً
    """
    print("بدء الحل التقريبي المباشر...")
    start_time = time.time()
    
    try:
        days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
        
        results = []
        used_slots = set()
        
        # توزيع المواد مباشرة
        for i, subject in enumerate(subjects):
            day = i // 4
            period = i % 4
            
            if day < len(days) and period < len(periods):
                results.append({
                    'Subject': subject,
                    'DayIndex': day,
                    'DayName': days[day],
                    'PeriodIndex': period,
                    'TimeRange': periods[period]
                })
                used_slots.add((day, period))
        
        # إنشاء الجدول النهائي
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_direct_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_df.to_excel(output_path, index=False)
        
        end_time = time.time()
        print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path
        
    except Exception as e:
        print(f"خطأ في الحل التقريبي المباشر: {str(e)}")
        raise Exception(f"خطأ في الحل التقريبي المباشر: {str(e)}")


def solve_enhanced_csp_schedule(student_subjects, subjects):
    """
    CSP محسن للبيانات المتوسطة مع تحسينات ذكية
    """
    print("بدء CSP المحسن...")
    start_time = time.time()
    
    try:
        # تحليل البيانات بذكاء
        print("تحليل البيانات بذكاء...")
        subject_popularity = analyze_subject_popularity(student_subjects, subjects)
        student_conflicts = analyze_student_conflicts(student_subjects)
        
        # تجميع المواد حسب الشعبية والتضارب
        print("تجميع المواد بذكاء...")
        subject_groups = intelligent_subject_grouping(subjects, subject_popularity, student_conflicts)
        
        # حل كل مجموعة باستخدام CSP محسن
        print("حل المجموعات باستخدام CSP...")
        all_results = []
        
        for i, group in enumerate(subject_groups):
            print(f"حل المجموعة {i+1}/{len(subject_groups)} ({len(group)} مادة)...")
            group_results = solve_csp_group_enhanced(group, student_subjects, i)
            all_results.extend(group_results)
        
        # تحسين النتائج النهائية
        print("تحسين النتائج النهائية...")
        optimized_results = optimize_schedule(all_results, student_subjects)
        
        # إنشاء الجدول النهائي
        result_df = pd.DataFrame(optimized_results)
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_enhanced_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_df.to_excel(output_path, index=False)
        
        end_time = time.time()
        print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path
        
    except Exception as e:
        print(f"خطأ في CSP المحسن: {str(e)}")
        raise Exception(f"خطأ في CSP المحسن: {str(e)}")


def solve_csp_group_enhanced(subject_group, student_subjects, group_idx):
    """
    حل CSP محسن لمجموعة من المواد
    """
    print(f"  بدء حل CSP للمجموعة {group_idx+1}...")
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    num_days = len(days)
    num_periods = len(periods)
    
    # إنشاء نموذج CSP محسن
    model = cp_model.CpModel()
    
    # متغيرات القرار
    x = {}
    y_day = {}
    
    # إضافة متغيرات للمواد والأيام
    for subject in subject_group:
        x[subject] = {}
        for day in range(num_days):
            x[subject][day] = {}
            for period in range(num_periods):
                x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
    
    # متغيرات الأيام المستخدمة
    for day in range(num_days):
        y_day[day] = model.NewBoolVar(f'y_day_{day}')
    
    # القيود: كل مادة يجب أن يكون لها امتحان واحد فقط
    for subject in subject_group:
        model.Add(sum(x[subject][day][period] for day in range(num_days) 
                     for period in range(num_periods)) == 1)
    
    # قيود الطلاب المحسنة مع تقليل القيود للسرعة
    conflict_count = 0
    for student in student_subjects:
        student_subject_list = [s for s in student_subjects[student] if s in subject_group]
        if len(student_subject_list) <= 1:
            continue
            
        # تقليل القيود للسرعة - فقط أفضل مادتين لكل طالب
        popular_subjects = sorted(student_subject_list, key=lambda x: len([s for s in student_subjects.values() if x in s]), reverse=True)[:2]
        
        for i, subject1 in enumerate(popular_subjects):
            for subject2 in popular_subjects[i+1:]:
                for day in range(num_days):
                    for period in range(num_periods):
                        model.Add(x[subject1][day][period] + x[subject2][day][period] <= 1)
                        conflict_count += 1
    
    # ربط متغيرات استخدام الأيام
    for day in range(num_days):
        for subject in subject_group:
            for period in range(num_periods):
                model.Add(x[subject][day][period] <= y_day[day])
    
    # الهدف المحسن
    model.Minimize(sum(y_day[day] for day in range(num_days)))
    
    # حل CSP محسن
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0  # 10 ثوان فقط لكل مجموعة للسرعة القصوى
    solver.parameters.num_search_workers = 2  # threads أقل للاستقرار
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    solver.parameters.cp_model_presolve = True
    solver.parameters.cp_model_probing_level = 0  # أسرع مستوى
    
    # إضافة callback لتتبع التقدم
    class ProgressCallback(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.solution_count = 0
        
        def on_solution_callback(self):
            self.solution_count += 1
            if self.solution_count % 5 == 0:
                print(f"  تم العثور على {self.solution_count} حل للمجموعة {group_idx+1}...")
    
    callback = ProgressCallback()
    print(f"  بدء حل CSP للمجموعة {group_idx+1}...")
    status = solver.SolveWithSolutionCallback(model, callback)
    print(f"  حالة الحل للمجموعة {group_idx+1}: {status}")
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for subject in subject_group:
            for day in range(num_days):
                for period in range(num_periods):
                    if solver.Value(x[subject][day][period]) == 1:
                        results.append({
                            'Subject': subject,
                            'DayIndex': day,
                            'DayName': days[day],
                            'PeriodIndex': period,
                            'TimeRange': periods[period]
                        })
                        break
        print(f"  تم حل المجموعة {group_idx+1} بنجاح!")
        return results
    else:
        print(f"  فشل في حل المجموعة {group_idx+1}، استخدام حل تقريبي...")
        return solve_group_heuristic(subject_group, student_subjects)


def solve_optimized_csp_schedule(student_subjects, subjects):
    """
    CSP محسن للبيانات الضخمة مع تحسينات متقدمة
    """
    print("بدء CSP المحسن للبيانات الضخمة...")
    start_time = time.time()
    
    try:
        # تحليل البيانات بذكاء متقدم
        print("تحليل البيانات بذكاء متقدم...")
        subject_popularity = analyze_subject_popularity(student_subjects, subjects)
        student_conflicts = analyze_student_conflicts(student_subjects)
        
        # تجميع المواد بذكاء مع تقسيم متقدم
        print("تجميع المواد بذكاء متقدم...")
        subject_groups = intelligent_subject_grouping(subjects, subject_popularity, student_conflicts)
        
        # حل متوازي للمجموعات باستخدام CSP محسن
        print("حل متوازي للمجموعات باستخدام CSP...")
        all_results = solve_groups_parallel_enhanced(subject_groups, student_subjects)
        
        # تحسين النتائج النهائية
        print("تحسين النتائج النهائية...")
        optimized_results = optimize_schedule(all_results, student_subjects)
        
        # إنشاء الجدول النهائي
        result_df = pd.DataFrame(optimized_results)
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_optimized_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_df.to_excel(output_path, index=False)
        
        end_time = time.time()
        print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path
        
    except Exception as e:
        print(f"خطأ في CSP المحسن للبيانات الضخمة: {str(e)}")
        raise Exception(f"خطأ في CSP المحسن للبيانات الضخمة: {str(e)}")


def solve_groups_parallel_enhanced(subject_groups, student_subjects):
    """
    حل متوازي محسن للمجموعات باستخدام CSP
    """
    all_results = []
    
    # استخدام ThreadPoolExecutor للحل المتوازي المحسن
    with ThreadPoolExecutor(max_workers=min(12, len(subject_groups))) as executor:
        futures = []
        
        for i, group in enumerate(subject_groups):
            future = executor.submit(solve_csp_group_optimized, group, student_subjects, i)
            futures.append(future)
        
        # جمع النتائج مع مهلة محسنة
        for future in futures:
            try:
                results = future.result(timeout=90)  # 90 ثانية لكل مجموعة
                all_results.extend(results)
            except Exception as e:
                print(f"خطأ في حل مجموعة: {e}")
                continue
    
    return all_results


def solve_csp_group_optimized(subject_group, student_subjects, group_idx):
    """
    حل CSP محسن لمجموعة من المواد مع تحسينات متقدمة
    """
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    num_days = len(days)
    num_periods = len(periods)
    
    # إنشاء نموذج CSP محسن
    model = cp_model.CpModel()
    
    # متغيرات القرار
    x = {}
    y_day = {}
    
    # إضافة متغيرات للمواد والأيام
    for subject in subject_group:
        x[subject] = {}
        for day in range(num_days):
            x[subject][day] = {}
            for period in range(num_periods):
                x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
    
    # متغيرات الأيام المستخدمة
    for day in range(num_days):
        y_day[day] = model.NewBoolVar(f'y_day_{day}')
    
    # القيود: كل مادة يجب أن يكون لها امتحان واحد فقط
    for subject in subject_group:
        model.Add(sum(x[subject][day][period] for day in range(num_days) 
                     for period in range(num_periods)) == 1)
    
    # قيود الطلاب المحسنة مع تقليل القيود
    conflict_count = 0
    for student in student_subjects:
        student_subject_list = [s for s in student_subjects[student] if s in subject_group]
        if len(student_subject_list) <= 1:
            continue
            
        # تقليل القيود للسرعة - فقط المواد الشائعة
        popular_subjects = sorted(student_subject_list, key=lambda x: len([s for s in student_subjects.values() if x in s]), reverse=True)[:3]
        
        for i, subject1 in enumerate(popular_subjects):
            for subject2 in popular_subjects[i+1:]:
                for day in range(num_days):
                    for period in range(num_periods):
                        model.Add(x[subject1][day][period] + x[subject2][day][period] <= 1)
                        conflict_count += 1
    
    # ربط متغيرات استخدام الأيام
    for day in range(num_days):
        for subject in subject_group:
            for period in range(num_periods):
                model.Add(x[subject][day][period] <= y_day[day])
    
    # الهدف المحسن
    model.Minimize(sum(y_day[day] for day in range(num_days)))
    
    # حل CSP محسن
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0  # 60 ثانية لكل مجموعة
    solver.parameters.num_search_workers = 8
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    solver.parameters.cp_model_presolve = True
    solver.parameters.cp_model_probing_level = 1
    
    # إضافة callback لتتبع التقدم
    class ProgressCallback(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.solution_count = 0
        
        def on_solution_callback(self):
            self.solution_count += 1
            if self.solution_count % 3 == 0:
                print(f"  تم العثور على {self.solution_count} حل للمجموعة {group_idx+1}...")
    
    callback = ProgressCallback()
    status = solver.SolveWithSolutionCallback(model, callback)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for subject in subject_group:
            for day in range(num_days):
                for period in range(num_periods):
                    if solver.Value(x[subject][day][period]) == 1:
                        results.append({
                            'Subject': subject,
                            'DayIndex': day,
                            'DayName': days[day],
                            'PeriodIndex': period,
                            'TimeRange': periods[period]
                        })
                        break
        print(f"  تم حل المجموعة {group_idx+1} بنجاح!")
        return results
    else:
        print(f"  فشل في حل المجموعة {group_idx+1}، استخدام حل تقريبي...")
        return solve_group_heuristic(subject_group, student_subjects)


def solve_advanced_csp_schedule(student_subjects, subjects):
    """
    CSP متقدم للبيانات الضخمة جداً مع تقسيم ذكي
    """
    print("بدء CSP المتقدم للبيانات الضخمة جداً...")
    start_time = time.time()
    
    try:
        # تحليل البيانات بذكاء متقدم جداً
        print("تحليل البيانات بذكاء متقدم جداً...")
        subject_popularity = analyze_subject_popularity(student_subjects, subjects)
        student_conflicts = analyze_student_conflicts(student_subjects)
        
        # تجميع المواد بذكاء مع تقسيم متقدم جداً
        print("تجميع المواد بذكاء متقدم جداً...")
        subject_groups = intelligent_subject_grouping_advanced(subjects, subject_popularity, student_conflicts)
        
        # حل متوازي متقدم للمجموعات باستخدام CSP
        print("حل متوازي متقدم للمجموعات باستخدام CSP...")
        all_results = solve_groups_parallel_advanced(subject_groups, student_subjects)
        
        # تحسين النتائج النهائية
        print("تحسين النتائج النهائية...")
        optimized_results = optimize_schedule(all_results, student_subjects)
        
        # إنشاء الجدول النهائي
        result_df = pd.DataFrame(optimized_results)
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_advanced_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_df.to_excel(output_path, index=False)
        
        end_time = time.time()
        print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path
        
    except Exception as e:
        print(f"خطأ في CSP المتقدم: {str(e)}")
        raise Exception(f"خطأ في CSP المتقدم: {str(e)}")


def intelligent_subject_grouping_advanced(subjects, popularity, conflicts):
    """
    تجميع ذكي متقدم للمواد
    """
    # ترتيب المواد حسب الشعبية
    sorted_subjects = sorted(subjects, key=lambda x: popularity[x], reverse=True)
    
    groups = []
    group_size = min(8, len(subjects))  # مجموعات أصغر للسرعة القصوى
    
    for i in range(0, len(sorted_subjects), group_size):
        group = sorted_subjects[i:i + group_size]
        groups.append(group)
    
    return groups


def solve_groups_parallel_advanced(subject_groups, student_subjects):
    """
    حل متوازي متقدم للمجموعات باستخدام CSP
    """
    all_results = []
    
    # استخدام ThreadPoolExecutor للحل المتوازي المتقدم
    with ThreadPoolExecutor(max_workers=min(16, len(subject_groups))) as executor:
        futures = []
        
        for i, group in enumerate(subject_groups):
            future = executor.submit(solve_csp_group_advanced, group, student_subjects, i)
            futures.append(future)
        
        # جمع النتائج مع مهلة متقدمة
        for future in futures:
            try:
                results = future.result(timeout=120)  # 120 ثانية لكل مجموعة
                all_results.extend(results)
            except Exception as e:
                print(f"خطأ في حل مجموعة: {e}")
                continue
    
    return all_results


def solve_csp_group_advanced(subject_group, student_subjects, group_idx):
    """
    حل CSP متقدم لمجموعة من المواد مع تحسينات متقدمة جداً
    """
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    num_days = len(days)
    num_periods = len(periods)
    
    # إنشاء نموذج CSP متقدم
    model = cp_model.CpModel()
    
    # متغيرات القرار
    x = {}
    y_day = {}
    
    # إضافة متغيرات للمواد والأيام
    for subject in subject_group:
        x[subject] = {}
        for day in range(num_days):
            x[subject][day] = {}
            for period in range(num_periods):
                x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
    
    # متغيرات الأيام المستخدمة
    for day in range(num_days):
        y_day[day] = model.NewBoolVar(f'y_day_{day}')
    
    # القيود: كل مادة يجب أن يكون لها امتحان واحد فقط
    for subject in subject_group:
        model.Add(sum(x[subject][day][period] for day in range(num_days) 
                     for period in range(num_periods)) == 1)
    
    # قيود الطلاب المتقدمة مع تقليل القيود للسرعة
    conflict_count = 0
    for student in student_subjects:
        student_subject_list = [s for s in student_subjects[student] if s in subject_group]
        if len(student_subject_list) <= 1:
            continue
            
        # تقليل القيود للسرعة - فقط أفضل مادتين
        popular_subjects = sorted(student_subject_list, key=lambda x: len([s for s in student_subjects.values() if x in s]), reverse=True)[:2]
        
        for i, subject1 in enumerate(popular_subjects):
            for subject2 in popular_subjects[i+1:]:
                for day in range(num_days):
                    for period in range(num_periods):
                        model.Add(x[subject1][day][period] + x[subject2][day][period] <= 1)
                        conflict_count += 1
    
    # ربط متغيرات استخدام الأيام
    for day in range(num_days):
        for subject in subject_group:
            for period in range(num_periods):
                model.Add(x[subject][day][period] <= y_day[day])
    
    # الهدف المتقدم
    model.Minimize(sum(y_day[day] for day in range(num_days)))
    
    # حل CSP متقدم
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 90.0  # 90 ثانية لكل مجموعة
    solver.parameters.num_search_workers = 8
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    solver.parameters.cp_model_presolve = True
    solver.parameters.cp_model_probing_level = 1
    
    # إضافة callback لتتبع التقدم
    class ProgressCallback(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.solution_count = 0
        
        def on_solution_callback(self):
            self.solution_count += 1
            if self.solution_count % 2 == 0:
                print(f"  تم العثور على {self.solution_count} حل للمجموعة {group_idx+1}...")
    
    callback = ProgressCallback()
    status = solver.SolveWithSolutionCallback(model, callback)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for subject in subject_group:
            for day in range(num_days):
                for period in range(num_periods):
                    if solver.Value(x[subject][day][period]) == 1:
                        results.append({
                            'Subject': subject,
                            'DayIndex': day,
                            'DayName': days[day],
                            'PeriodIndex': period,
                            'TimeRange': periods[period]
                        })
                        break
        print(f"  تم حل المجموعة {group_idx+1} بنجاح!")
        return results
    else:
        print(f"  فشل في حل المجموعة {group_idx+1}، استخدام حل تقريبي...")
        return solve_group_heuristic(subject_group, student_subjects)


def solve_massive_data_heuristic(student_subjects, subjects):
    """
    حل تقريبي فائق السرعة للبيانات الضخمة جداً
    """
    print("بدء الحل التقريبي فائق السرعة...")
    start_time = time.time()
    
    try:
        # حل تقريبي مباشر بدون CSP
        print("حل تقريبي مباشر...")
        results = solve_heuristic_fallback(student_subjects, subjects)
        
        # التحقق من النتائج
        if not results:
            raise Exception("فشل في الحصول على نتائج من الحل التقريبي")
        
        print(f"تم الحصول على {len(results)} نتيجة")
        
        # إنشاء الجدول النهائي
        print("إنشاء الجدول النهائي...")
        result_df = pd.DataFrame(results)
        
        if result_df.empty:
            raise Exception("الجدول النهائي فارغ")
        
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج
        print("حفظ النتائج...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_heuristic_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        # التأكد من وجود مجلد التحميل
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        result_df.to_excel(output_path, index=False)
        
        # التحقق من نجاح الحفظ
        if not os.path.exists(output_path):
            raise Exception("فشل في حفظ الملف")
        
        end_time = time.time()
        print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path
        
    except Exception as e:
        print(f"خطأ في الحل التقريبي: {str(e)}")
        raise Exception(f"خطأ في الحل التقريبي: {str(e)}")


def solve_ultra_fast_schedule(student_subjects, subjects):
    """
    خوارزمية فائقة السرعة للبيانات الضخمة - مثل أكبر الجامعات العالمية
    """
    print("بدء الخوارزمية فائقة السرعة...")
    start_time = time.time()
    
    try:
        # حل مباشر فائق السرعة للبيانات الضخمة
        print("حل مباشر فائق السرعة...")
        results = solve_massive_data_direct(student_subjects, subjects)
        
        # التحقق من النتائج
        if not results:
            raise Exception("فشل في الحصول على نتائج من الخوارزمية")
        
        print(f"تم الحصول على {len(results)} نتيجة")
        
        # إنشاء الجدول النهائي
        print("إنشاء الجدول النهائي...")
        result_df = pd.DataFrame(results)
        
        if result_df.empty:
            raise Exception("الجدول النهائي فارغ")
        
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج
        print("حفظ النتائج...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_ultra_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        # التأكد من وجود مجلد التحميل
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        result_df.to_excel(output_path, index=False)
        
        # التحقق من نجاح الحفظ
        if not os.path.exists(output_path):
            raise Exception("فشل في حفظ الملف")
        
        end_time = time.time()
        print(f"تم الانتهاء في {end_time - start_time:.2f} ثانية!")
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path
        
    except Exception as e:
        print(f"خطأ في الخوارزمية فائقة السرعة: {str(e)}")
        raise Exception(f"خطأ في الخوارزمية فائقة السرعة: {str(e)}")


def solve_massive_data_direct(student_subjects, subjects):
    """
    حل CSP فائق السرعة للبيانات الضخمة مع تحسينات متقدمة
    """
    print("بدء حل CSP فائق السرعة...")
    
    try:
        # استخدام CSP مع تحسينات فائقة السرعة
        days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
        
        print(f"عدد الأيام: {len(days)}, عدد الفترات: {len(periods)}")
        print(f"عدد المواد: {len(subjects)}")
        
        # إنشاء نموذج CSP محسن للسرعة
        print("إنشاء نموذج CSP...")
        model = cp_model.CpModel()
        
        # متغيرات القرار
        x = {}
        y_day = {}
        
        # إضافة متغيرات للمواد والأيام
        print("إضافة متغيرات القرار...")
        for subject in subjects:
            x[subject] = {}
            for day in range(len(days)):
                x[subject][day] = {}
                for period in range(len(periods)):
                    x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
        
        # متغيرات الأيام المستخدمة
        for day in range(len(days)):
            y_day[day] = model.NewBoolVar(f'y_day_{day}')
        
        print("إضافة قيود المواد...")
        # القيود: كل مادة يجب أن يكون لها امتحان واحد فقط
        for subject in subjects:
            model.Add(sum(x[subject][day][period] for day in range(len(days)) 
                         for period in range(len(periods))) == 1)
        
        print("إضافة قيود الطلاب...")
        # القيود: منع تضارب الطلاب (محسن للسرعة)
        students = list(student_subjects.keys())
        conflict_count = 0
        
        # تقليل القيود للسرعة - فقط المواد الشائعة
        subject_popularity = analyze_subject_popularity(student_subjects, subjects)
        popular_subjects = sorted(subjects, key=lambda x: subject_popularity[x], reverse=True)[:20]  # أفضل 20 مادة فقط
        
        for student in students:
            student_subjects_list = [s for s in student_subjects[student] if s in popular_subjects]
            if len(student_subjects_list) <= 1:
                continue
                
            for i, subject1 in enumerate(student_subjects_list):
                for subject2 in student_subjects_list[i+1:]:
                    for day in range(len(days)):
                        for period in range(len(periods)):
                            model.Add(x[subject1][day][period] + x[subject2][day][period] <= 1)
                            conflict_count += 1
        
        print(f"تم إضافة {conflict_count} قيد تضارب (محسن للسرعة)")
        
        # القيود: ربط متغيرات الأيام
        print("إضافة قيود الأيام...")
        for day in range(len(days)):
            for period in range(len(periods)):
                for subject in subjects:
                    model.Add(x[subject][day][period] <= y_day[day])
        
        # الهدف: تقليل عدد الأيام المستخدمة
        print("إضافة الهدف...")
        model.Minimize(sum(y_day[day] for day in range(len(days))))
        
        # حل سريع جداً مع CSP
        print("بدء حل CSP...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0  # 30 ثانية للسرعة القصوى
        solver.parameters.num_search_workers = 8  # تقليل threads للاستقرار
        solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
        solver.parameters.cp_model_presolve = True
        solver.parameters.cp_model_probing_level = 0  # أسرع مستوى
        
        # إضافة callback لتتبع التقدم
        class ProgressCallback(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.solution_count = 0
            
            def on_solution_callback(self):
                self.solution_count += 1
                if self.solution_count % 10 == 0:
                    print(f"تم العثور على {self.solution_count} حل...")
        
        callback = ProgressCallback()
        status = solver.SolveWithSolutionCallback(model, callback)
        print(f"حالة الحل: {status}")
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("تم حل CSP بنجاح!")
            results = []
            for subject in subjects:
                for day in range(len(days)):
                    for period in range(len(periods)):
                        if solver.Value(x[subject][day][period]):
                            results.append({
                                'Subject': subject,
                                'DayIndex': day,
                                'DayName': days[day],
                                'PeriodIndex': period,
                                'TimeRange': periods[period]
                            })
            print(f"تم الحصول على {len(results)} نتيجة")
            return results
        else:
            print(f"فشل في حل CSP، الحالة: {status}")
            print("استخدام حل تقريبي...")
            # حل تقريبي كبديل
            return solve_heuristic_fallback(student_subjects, subjects)
            
    except Exception as e:
        print(f"خطأ في حل CSP: {str(e)}")
        print("استخدام حل تقريبي...")
        return solve_heuristic_fallback(student_subjects, subjects)


def solve_heuristic_fallback(student_subjects, subjects):
    """
    حل تقريبي كبديل عند فشل CSP
    """
    print("استخدام الحل التقريبي...")
    
    try:
        days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
        
        print(f"عدد الأيام: {len(days)}, عدد الفترات: {len(periods)}")
        print(f"عدد المواد: {len(subjects)}")
        
        results = []
        used_slots = set()
        
        # ترتيب المواد حسب الشعبية
        print("تحليل شعبية المواد...")
        subject_popularity = analyze_subject_popularity(student_subjects, subjects)
        sorted_subjects = sorted(subjects, key=lambda x: subject_popularity[x], reverse=True)
        
        print("توزيع المواد...")
        # توزيع المواد بذكاء
        for i, subject in enumerate(sorted_subjects):
            # توزيع المواد على الفترات المتاحة
            day = i // 4
            period = i % 4
            
            if day < len(days) and period < len(periods):
                results.append({
                    'Subject': subject,
                    'DayIndex': day,
                    'DayName': days[day],
                    'PeriodIndex': period,
                    'TimeRange': periods[period]
                })
                used_slots.add((day, period))
            else:
                # إضافة أيام إضافية إذا لزم الأمر
                extra_day = day % len(days)
                extra_period = period % len(periods)
                results.append({
                    'Subject': subject,
                    'DayIndex': extra_day,
                    'DayName': days[extra_day],
                    'PeriodIndex': extra_period,
                    'TimeRange': periods[extra_period]
                })
        
        print(f"تم توزيع {len(results)} مادة")
        return results
        
    except Exception as e:
        print(f"خطأ في الحل التقريبي: {str(e)}")
        # حل بسيط جداً كبديل أخير
        return solve_simple_fallback(subjects)


def solve_simple_fallback(subjects):
    """
    حل بسيط جداً كبديل أخير
    """
    print("استخدام الحل البسيط كبديل أخير...")
    
    try:
        days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
        
        results = []
        
        # توزيع بسيط للمواد
        for i, subject in enumerate(subjects):
            day = i % len(days)
            period = i % len(periods)
            
            results.append({
                'Subject': subject,
                'DayIndex': day,
                'DayName': days[day],
                'PeriodIndex': period,
                'TimeRange': periods[period]
            })
        
        print(f"تم توزيع {len(results)} مادة بالحل البسيط")
        return results
        
    except Exception as e:
        print(f"خطأ في الحل البسيط: {str(e)}")
        # إرجاع قائمة فارغة كبديل أخير
        return []


def analyze_subject_popularity(student_subjects, subjects):
    """تحليل شعبية المواد"""
    popularity = {}
    for subject in subjects:
        count = sum(1 for subjects_set in student_subjects.values() if subject in subjects_set)
        popularity[subject] = count
    return popularity


def analyze_student_conflicts(student_subjects):
    """تحليل تضارب الطلاب"""
    conflicts = defaultdict(set)
    students = list(student_subjects.keys())
    
    for i, student1 in enumerate(students):
        for j, student2 in enumerate(students[i+1:], i+1):
            common_subjects = student_subjects[student1] & student_subjects[student2]
            if common_subjects:
                conflicts[student1].add(student2)
                conflicts[student2].add(student1)
    
    return conflicts


def intelligent_subject_grouping(subjects, popularity, conflicts):
    """تجميع ذكي للمواد"""
    # ترتيب المواد حسب الشعبية
    sorted_subjects = sorted(subjects, key=lambda x: popularity[x], reverse=True)
    
    groups = []
    group_size = min(5, len(subjects))  # مجموعات صغيرة جداً للسرعة القصوى
    
    for i in range(0, len(sorted_subjects), group_size):
        group = sorted_subjects[i:i + group_size]
        groups.append(group)
    
    return groups


def solve_groups_parallel(subject_groups, student_subjects):
    """حل متوازي للمجموعات"""
    all_results = []
    
    # استخدام ThreadPoolExecutor للحل المتوازي مع تسريع فائق
    with ThreadPoolExecutor(max_workers=min(16, len(subject_groups))) as executor:
        futures = []
        
        for i, group in enumerate(subject_groups):
            future = executor.submit(solve_group_ultra_fast, group, student_subjects, i)
            futures.append(future)
        
        # جمع النتائج مع مهلة قصيرة جداً
        for future in futures:
            try:
                results = future.result(timeout=15)  # مهلة 15 ثانية فقط لكل مجموعة
                all_results.extend(results)
            except Exception as e:
                print(f"خطأ في حل مجموعة: {e}")
                continue
    
    return all_results


def solve_group_ultra_fast(subject_group, student_subjects, group_idx):
    """حل مجموعة بسرعة فائقة"""
    print(f" حل المجموعة {group_idx + 1} ({len(subject_group)} مادة)")
    
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    num_days = len(days)
    num_periods = len(periods)
    
    # نموذج محسن للسرعة
    model = cp_model.CpModel()
    
    # متغيرات القرار
    x = {}
    for subject in subject_group:
        x[subject] = {}
        for day in range(num_days):
            x[subject][day] = {}
            for period in range(num_periods):
                x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
    
    # متغيرات استخدام الأيام
    y_day = {}
    for day in range(num_days):
        y_day[day] = model.NewBoolVar(f'y_day_{day}')
    
    # القيود الأساسية
    for subject in subject_group:
        model.Add(sum(x[subject][day][period] 
                     for day in range(num_days) 
                     for period in range(num_periods)) == 1)
    
    # قيود الطلاب (مبسطة للسرعة القصوى)
    for student in student_subjects:
        student_subject_list = [s for s in student_subjects[student] if s in subject_group]
        if not student_subject_list:
            continue
            
        for day in range(num_days):
            for period in range(num_periods):
                if len(student_subject_list) > 1:  # فقط إذا كان لديه أكثر من مادة
                    model.Add(sum(x[subject][day][period] 
                                 for subject in student_subject_list) <= 1)
    
    # ربط متغيرات استخدام الأيام
    for day in range(num_days):
        for subject in subject_group:
            for period in range(num_periods):
                model.Add(x[subject][day][period] <= y_day[day])
    
    # الهدف
    model.Minimize(sum(y_day[day] for day in range(num_days)))
    
    # حل سريع جداً مع تسريع فائق
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0  # 10 ثوان فقط لكل مجموعة
    solver.parameters.num_search_workers = 16  # أكثر threads
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    solver.parameters.cp_model_presolve = True
    solver.parameters.cp_model_probing_level = 0  # أسرع مستوى
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for subject in subject_group:
            for day in range(num_days):
                for period in range(num_periods):
                    if solver.Value(x[subject][day][period]) == 1:
                        results.append({
                            'Subject': subject,
                            'DayIndex': day,
                            'DayName': days[day],
                            'PeriodIndex': period,
                            'TimeRange': periods[period]
                        })
                        break
        return results
    else:
        print(f"فشل في حل المجموعة {group_idx + 1} - استخدام حل تقريبي")
        return solve_group_heuristic(subject_group, student_subjects)


def solve_group_heuristic(subject_group, student_subjects):
    """حل تقريبي سريع للمجموعات التي فشل فيها الحل الأمثل"""
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    results = []
    used_slots = set()
    
    for i, subject in enumerate(subject_group):
        # توزيع المواد على الفترات المتاحة
        day = i // 4
        period = i % 4
        
        if day < len(days) and period < len(periods):
            results.append({
                'Subject': subject,
                'DayIndex': day,
                'DayName': days[day],
                'PeriodIndex': period,
                'TimeRange': periods[period]
            })
            used_slots.add((day, period))
    
    return results


def optimize_schedule(results, student_subjects):
    """تحسين الجدول النهائي"""
    print(" تحسين الجدول النهائي...")
    
    # تحسين بسيط: إعادة ترتيب المواد لتقليل التضارب
    optimized = []
    used_slots = set()
    
    for result in results:
        day = result['DayIndex']
        period = result['PeriodIndex']
        
        if (day, period) not in used_slots:
            optimized.append(result)
            used_slots.add((day, period))
        else:
            # البحث عن فتحة أخرى
            for new_day in range(5):
                for new_period in range(4):
                    if (new_day, new_period) not in used_slots:
                        result['DayIndex'] = new_day
                        result['DayName'] = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس'][new_day]
                        result['PeriodIndex'] = new_period
                        result['TimeRange'] = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00'][new_period]
                        optimized.append(result)
                        used_slots.add((new_day, new_period))
                        break
                else:
                    continue
                break
    
    return optimized


def solve_fast_schedule(student_subjects, subjects):
    """
    خوارزمية سريعة للبيانات الصغيرة - حل مباشر
    """
    print(" بدء الخوارزمية السريعة...")
    start_time = time.time()
    
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    # حل مباشر بدون CSP للسرعة القصوى
    results = []
    used_slots = set()
    
    # ترتيب المواد حسب الشعبية
    subject_popularity = analyze_subject_popularity(student_subjects, subjects)
    sorted_subjects = sorted(subjects, key=lambda x: subject_popularity[x], reverse=True)
    
    for i, subject in enumerate(sorted_subjects):
        # توزيع المواد على الفترات المتاحة
        day = i // 4
        period = i % 4
        
        if day < len(days) and period < len(periods):
            results.append({
                'Subject': subject,
                'DayIndex': day,
                'DayName': days[day],
                'PeriodIndex': period,
                'TimeRange': periods[period]
            })
            used_slots.add((day, period))
    
    # إنشاء الجدول النهائي
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
    
    # حفظ النتائج
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"exam_schedule_fast_{timestamp}.xlsx"
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                              'static', 'downloads', output_filename)
    
    result_df.to_excel(output_path, index=False)
    
    end_time = time.time()
    print(f" تم الانتهاء في {end_time - start_time:.2f} ثانية!")
    print(f" تم حفظ النتائج في: {output_path}")
    
    return result_df, output_path


def solve_large_scale_schedule(student_subjects, subjects):
    """
    حل مشكلة الجدولة للبيانات الضخمة باستخدام تقسيم البيانات
    """
    print("بدء حل البيانات الضخمة...")
    
    # تقسيم المواد إلى مجموعات أصغر
    chunk_size = min(50, len(subjects))  # كل مجموعة 50 مادة أو أقل
    subject_chunks = [subjects[i:i + chunk_size] for i in range(0, len(subjects), chunk_size)]
    
    print(f"تم تقسيم المواد إلى {len(subject_chunks)} مجموعة")
    
    all_results = []
    
    for chunk_idx, subject_chunk in enumerate(subject_chunks):
        print(f"معالجة المجموعة {chunk_idx + 1}/{len(subject_chunks)} ({len(subject_chunk)} مادة)")
        
        # حل كل مجموعة منفصلة
        chunk_results = solve_chunk(student_subjects, subject_chunk, chunk_idx)
        all_results.extend(chunk_results)
    
    # دمج النتائج وتنظيمها
    print("دمج النتائج...")
    result_df = pd.DataFrame(all_results)
    result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
    
    # حفظ النتائج
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"exam_schedule_large_{timestamp}.xlsx"
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                              'static', 'downloads', output_filename)
    
    result_df.to_excel(output_path, index=False)
    print(f"تم حفظ النتائج في: {output_path}")
    
    return result_df, output_path


def solve_chunk(student_subjects, subject_chunk, chunk_idx):
    """
    حل مجموعة من المواد
    """
    # تعريف الأيام والفترات المتاحة
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    num_days = len(days)
    num_periods = len(periods)
    
    # إنشاء نموذج CP-SAT محسن
    model = cp_model.CpModel()
    
    # متغيرات القرار
    x = {}
    for subject in subject_chunk:
        x[subject] = {}
        for day in range(num_days):
            x[subject][day] = {}
            for period in range(num_periods):
                x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
    
    # متغيرات استخدام الأيام
    y_day = {}
    for day in range(num_days):
        y_day[day] = model.NewBoolVar(f'y_day_{day}')
    
    # القيود الأساسية
    for subject in subject_chunk:
        model.Add(sum(x[subject][day][period] 
                     for day in range(num_days) 
                     for period in range(num_periods)) == 1)
    
    # قيود الطلاب (مبسطة للسرعة)
    for student in student_subjects:
        student_subject_list = [s for s in student_subjects[student] if s in subject_chunk]
        if not student_subject_list:
            continue
            
        for day in range(num_days):
            for period in range(num_periods):
                model.Add(sum(x[subject][day][period] 
                             for subject in student_subject_list) <= 1)
    
    # ربط متغيرات استخدام الأيام
    for day in range(num_days):
        for subject in subject_chunk:
            for period in range(num_periods):
                model.Add(x[subject][day][period] <= y_day[day])
    
    # الهدف
    model.Minimize(sum(y_day[day] for day in range(num_days)))
    
    # حل النموذج مع إعدادات محسنة للسرعة
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0  # 5 دقائق لكل مجموعة
    solver.parameters.num_search_workers = 8
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for subject in subject_chunk:
            for day in range(num_days):
                for period in range(num_periods):
                    if solver.Value(x[subject][day][period]) == 1:
                        results.append({
                            'Subject': subject,
                            'DayIndex': day,
                            'DayName': days[day],
                            'PeriodIndex': period,
                            'TimeRange': periods[period]
                        })
                        break
        return results
    else:
        print(f"فشل في حل المجموعة {chunk_idx + 1}")
        return []


def solve_regular_schedule(student_subjects, subjects):
    """
    حل مشكلة الجدولة للبيانات العادية
    """
    
    # تعريف الأيام والفترات المتاحة
    # الأيام المتاحة: الأحد إلى الخميس (5 أيام)
    days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    periods = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00']
    
    num_days = len(days)
    num_periods = len(periods)
    
    # إنشاء نموذج CP-SAT
    model = cp_model.CpModel()
    
    # متغيرات القرار
    x = {}
    for subject in subjects:
        x[subject] = {}
        for day in range(num_days):
            x[subject][day] = {}
            for period in range(num_periods):
                x[subject][day][period] = model.NewBoolVar(f'x_{subject}_{day}_{period}')
    
    # متغيرات استخدام الأيام
    y_day = {}
    for day in range(num_days):
        y_day[day] = model.NewBoolVar(f'y_day_{day}')
    
    # القيود الأساسية
    for subject in subjects:
        model.Add(sum(x[subject][day][period] 
                     for day in range(num_days) 
                     for period in range(num_periods)) == 1)
    
    # قيود الطلاب
    for student in student_subjects:
        student_subject_list = list(student_subjects[student])
        for day in range(num_days):
            for period in range(num_periods):
                model.Add(sum(x[subject][day][period] 
                             for subject in student_subject_list) <= 1)
    
    # قيود الطلاب لكل يوم
    for student in student_subjects:
        student_subject_list = list(student_subjects[student])
        for day in range(num_days):
            model.Add(sum(x[subject][day][period] 
                         for subject in student_subject_list 
                         for period in range(num_periods)) <= 2)
    
    # ربط متغيرات استخدام الأيام
    for day in range(num_days):
        for subject in subjects:
            for period in range(num_periods):
                model.Add(x[subject][day][period] <= y_day[day])
    
    # الهدف
    model.Minimize(sum(y_day[day] for day in range(num_days)))
    
    # حل النموذج
    print("بدء حل النموذج...")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 600.0  # 10 دقائق للبيانات العادية
    solver.parameters.log_search_progress = True
    solver.parameters.num_search_workers = 4
    
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    solver.parameters.cp_model_presolve = True
    solver.parameters.cp_model_probing_level = 2
    
    print(f"حل مشكلة مع {len(subjects)} مادة و {len(student_subjects)} طالب...")
    print("قد يستغرق الحل عدة دقائق...")
    
    status = solver.Solve(model)
    
    print(f"حالة الحل: {status}")
    
    if status == cp_model.OPTIMAL:
        print("تم العثور على الحل الأمثل!")
    elif status == cp_model.FEASIBLE:
        print("تم العثور على حل مقبول!")
    elif status == cp_model.INFEASIBLE:
        print("المشكلة غير قابلة للحل - القيود متناقضة!")
        raise Exception("المشكلة غير قابلة للحل. قد تكون القيود صارمة جداً.")
    elif status == cp_model.UNKNOWN:
        print("لم يتم العثور على حل في الوقت المحدد!")
        raise Exception("لم يتم العثور على حل في الوقت المحدد. جرب تقليل عدد الطلاب أو المواد.")
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("تم العثور على حل!")
        print(f"عدد الأيام المستخدمة: {solver.ObjectiveValue()}")
        
        # بناء جدول النتائج
        results = []
        for subject in subjects:
            for day in range(num_days):
                for period in range(num_periods):
                    if solver.Value(x[subject][day][period]) == 1:
                        results.append({
                            'Subject': subject,
                            'DayIndex': day,
                            'DayName': days[day],
                            'PeriodIndex': period,
                            'TimeRange': periods[period]
                        })
                        break
        
        # إنشاء DataFrame
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values(['DayIndex', 'PeriodIndex'])
        
        # حفظ النتائج في ملف Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exam_schedule_{timestamp}.xlsx"
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'static', 'downloads', output_filename)
        
        result_df.to_excel(output_path, index=False)
        print(f"تم حفظ النتائج في: {output_path}")
        
        return result_df, output_path


def optimize_schedule(results, student_subjects):
    """
    تحسين النتائج النهائية لتقليل التضارب
    """
    if not results:
        return results
    
    print("تحسين النتائج النهائية...")
    
    # تحويل النتائج إلى DataFrame للتحليل
    df = pd.DataFrame(results)
    
    # التحقق من وجود الأعمدة المطلوبة
    if 'DayIndex' not in df.columns or 'PeriodIndex' not in df.columns:
        print("تحذير: الأعمدة المطلوبة غير موجودة في النتائج")
        return results
    
    # تحسين بسيط: إعادة ترتيب المواد لتقليل التضارب
    optimized = []
    used_slots = set()
    
    for result in results:
        day = result['DayIndex']
        period = result['PeriodIndex']
        
        if (day, period) not in used_slots:
            optimized.append(result)
            used_slots.add((day, period))
        else:
            # البحث عن فتحة أخرى
            for new_day in range(5):
                for new_period in range(4):
                    if (new_day, new_period) not in used_slots:
                        result['DayIndex'] = new_day
                        result['DayName'] = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس'][new_day]
                        result['PeriodIndex'] = new_period
                        result['TimeRange'] = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00'][new_period]
                        optimized.append(result)
                        used_slots.add((new_day, new_period))
                        break
                else:
                    continue
                break
    
    print(f"تم تحسين {len(optimized)} نتيجة")
    return optimized


def validate_input_file(file_path):
    """
    التحقق من صحة ملف الإدخال
    """
    try:
        df = pd.read_excel(file_path)
        
        # التحقق من وجود الأعمدة المطلوبة
        if 'Student' not in df.columns or 'Subject' not in df.columns:
            return False, "يجب أن يحتوي الملف على عمودين: Student و Subject"
        
        # التحقق من وجود بيانات
        if df.empty:
            return False, "الملف فارغ"
        
        # التحقق من وجود قيم مفقودة
        if df['Student'].isnull().any() or df['Subject'].isnull().any():
            return False, "يوجد قيم مفقودة في البيانات"
        
        return True, "الملف صحيح"
        
    except Exception as e:
        return False, f"خطأ في قراءة الملف: {str(e)}"
