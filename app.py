"""
تطبيق Flask لنظام جدولة الامتحانات باستخدام CSP
"""

from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
import uuid
import threading
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from solver.scheduler import solve_schedule, validate_input_file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'exam_schedule_csp_secret_key'
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# متغيرات عامة لتخزين النتائج
schedule_results = {}
output_file_path = ""
processing_status = "idle"  # idle, processing, completed, error
processing_error = ""
processing_messages = []  # قائمة الرسائل للمعالجة


def allowed_file(filename):
    """التحقق من امتداد الملف المسموح"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_schedule_background(file_path):
    """معالجة الجدولة في الخلفية مع معالجة شاملة للأخطاء"""
    global schedule_results, output_file_path, processing_status, processing_error, processing_messages
    
    try:
        processing_status = "processing"
        processing_error = ""
        processing_messages = []
        
        def add_message(message):
            processing_messages.append(message)
            print(message)
        
        add_message("=" * 50)
        add_message("بدء معالجة الجدولة...")
        add_message("=" * 50)
        
        # التحقق من وجود الملف
        if not os.path.exists(file_path):
            error_msg = "الملف غير موجود"
            add_message(f"خطأ: {error_msg}")
            raise Exception(error_msg)
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            error_msg = "الملف فارغ"
            add_message(f"خطأ: {error_msg}")
            raise Exception(error_msg)
        
        add_message(f"تم العثور على الملف: {file_path}")
        add_message(f"حجم الملف: {file_size} bytes")
        
        # حل الجدولة
        add_message("بدء حل الجدولة...")
        schedule_df, output_path = solve_schedule(file_path)
        
        # التحقق من النتائج
        if schedule_df is None or schedule_df.empty:
            error_msg = "فشل في إنشاء الجدولة"
            add_message(f"خطأ: {error_msg}")
            raise Exception(error_msg)
        
        add_message(f"تم إنشاء الجدولة بنجاح!")
        add_message(f"عدد السجلات: {len(schedule_df)}")
        
        schedule_results = schedule_df.to_dict('records')
        output_file_path = output_path
        processing_status = "completed"
        
        add_message("=" * 50)
        add_message("تم الانتهاء من المعالجة بنجاح!")
        add_message("=" * 50)
        
        # حذف ملف الإدخال المؤقت
        if os.path.exists(file_path):
            os.remove(file_path)
            add_message(f"تم حذف الملف المؤقت: {file_path}")
        
    except FileNotFoundError:
        error_msg = "الملف غير موجود"
        add_message(f"خطأ: {error_msg}")
        processing_status = "error"
        processing_error = error_msg
        if os.path.exists(file_path):
            os.remove(file_path)
    except ValueError as e:
        error_msg = f"خطأ في البيانات: {str(e)}"
        add_message(f"خطأ: {error_msg}")
        processing_status = "error"
        processing_error = error_msg
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        error_msg = f"خطأ في المعالجة: {str(e)}"
        add_message(f"خطأ: {error_msg}")
        processing_status = "error"
        processing_error = error_msg
        if os.path.exists(file_path):
            os.remove(file_path)


@app.route('/')
def index():
    """الصفحة الرئيسية لرفع ملف Excel"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """معالجة رفع الملف مع معالجة شاملة للأخطاء"""
    global schedule_results, output_file_path, processing_status, processing_error
    
    try:
        # إعادة تعيين حالة المعالجة
        processing_status = "idle"
        processing_error = ""
        
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(request.url)
        
        # التحقق من امتداد الملف
        if not allowed_file(file.filename):
            flash('نوع الملف غير مدعوم. يرجى رفع ملف Excel (.xlsx أو .xls)', 'error')
            return redirect(request.url)
        
        # التحقق من حجم الملف
        file.seek(0, 2)  # الانتقال إلى نهاية الملف
        file_size = file.tell()
        file.seek(0)  # العودة إلى البداية
        
        if file_size == 0:
            flash('الملف فارغ', 'error')
            return redirect(request.url)
        
        if file_size > MAX_CONTENT_LENGTH:
            flash(f'حجم الملف كبير جداً. الحد الأقصى: {MAX_CONTENT_LENGTH // (1024*1024)} MB', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # إنشاء اسم فريد للملف
            filename = secure_filename(file.filename)
            if not filename:
                flash('اسم الملف غير صحيح', 'error')
                return redirect(request.url)
                
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            try:
                # حفظ الملف
                file.save(file_path)
                
                # التحقق من وجود الملف بعد الحفظ
                if not os.path.exists(file_path):
                    flash('فشل في حفظ الملف', 'error')
                    return redirect(url_for('index'))
                
                # التحقق من حجم الملف بعد الحفظ
                saved_file_size = os.path.getsize(file_path)
                if saved_file_size == 0:
                    flash('الملف فارغ بعد الحفظ', 'error')
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return redirect(url_for('index'))
                
                # التحقق من صحة الملف
                try:
                    is_valid, message = validate_input_file(file_path)
                    if not is_valid:
                        flash(f'خطأ في الملف: {message}', 'error')
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return redirect(url_for('index'))
                except Exception as validation_error:
                    flash(f'خطأ في التحقق من الملف: {str(validation_error)}', 'error')
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return redirect(url_for('index'))
                
                # بدء المعالجة في الخلفية
                thread = threading.Thread(target=process_schedule_background, args=(file_path,))
                thread.daemon = True
                thread.start()
                
                # إعادة التوجيه لصفحة المعالجة
                return redirect(url_for('processing'))
                
            except Exception as e:
                flash(f'خطأ في حفظ الملف: {str(e)}', 'error')
                if os.path.exists(file_path):
                    os.remove(file_path)
                return redirect(url_for('index'))
        else:
            flash('نوع الملف غير مدعوم. يرجى رفع ملف Excel (.xlsx أو .xls)', 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f'خطأ عام: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/processing')
def processing():
    """صفحة المعالجة مع عرض الرسائل"""
    global processing_status, processing_error, processing_messages
    
    if processing_status == "completed":
        return redirect(url_for('show_results'))
    elif processing_status == "error":
        return render_template('processing.html', 
                             status=processing_status, 
                             error_message=processing_error,
                             messages=processing_messages)
    
    return render_template('processing.html', 
                         status=processing_status, 
                         error_message="",
                         messages=processing_messages)


@app.route('/messages')
def get_messages():
    """الحصول على الرسائل الحالية"""
    global processing_messages
    return {'messages': processing_messages}


@app.route('/results')
def show_results():
    """عرض نتائج الجدولة مع معالجة الأخطاء"""
    global schedule_results, output_file_path, processing_status, processing_error
    
    try:
        # التحقق من حالة المعالجة
        if processing_status == "error":
            flash(f'خطأ في المعالجة: {processing_error}', 'error')
            return redirect(url_for('index'))
        
        if processing_status != "completed":
            flash('المعالجة لم تكتمل بعد', 'error')
            return redirect(url_for('index'))
        
        # التحقق من وجود النتائج
        if not schedule_results:
            flash('لا توجد نتائج لعرضها', 'error')
            return redirect(url_for('index'))
        
        # التحقق من وجود ملف المخرجات
        if not output_file_path or not os.path.exists(output_file_path):
            flash('ملف النتائج غير موجود', 'error')
            return redirect(url_for('index'))
        
        # التحقق من صحة البيانات
        if not isinstance(schedule_results, list) or len(schedule_results) == 0:
            flash('النتائج فارغة أو غير صحيحة', 'error')
            return redirect(url_for('index'))
        
        return render_template('result.html', 
                             schedule_data=schedule_results,
                             output_file=os.path.basename(output_file_path))
                             
    except Exception as e:
        flash(f'خطأ في عرض النتائج: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download')
def download_file():
    """تحميل ملف Excel الناتج مع معالجة الأخطاء"""
    global output_file_path, processing_status
    
    try:
        # التحقق من حالة المعالجة
        if processing_status != "completed":
            flash('المعالجة لم تكتمل بعد', 'error')
            return redirect(url_for('index'))
        
        # التحقق من وجود مسار الملف
        if not output_file_path:
            flash('مسار ملف التحميل غير محدد', 'error')
            return redirect(url_for('index'))
        
        # التحقق من وجود الملف
        if not os.path.exists(output_file_path):
            flash('ملف التحميل غير موجود', 'error')
            return redirect(url_for('index'))
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(output_file_path)
        if file_size == 0:
            flash('ملف التحميل فارغ', 'error')
            return redirect(url_for('index'))
        
        # التحقق من نوع الملف
        if not output_file_path.lower().endswith(('.xlsx', '.xls')):
            flash('نوع ملف التحميل غير صحيح', 'error')
            return redirect(url_for('index'))
        
        return send_file(output_file_path, as_attachment=True)
        
    except Exception as e:
        flash(f'خطأ في تحميل الملف: {str(e)}', 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    # التأكد من وجود المجلدات المطلوبة
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    print("بدء تشغيل تطبيق جدولة الامتحانات...")
    print(f"المجلد الرئيسي: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"مجلد الرفع: {UPLOAD_FOLDER}")
    print(f"مجلد التحميل: {OUTPUT_FOLDER}")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
