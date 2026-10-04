// نظام جدولة الامتحانات - JavaScript الرئيسي

document.addEventListener('DOMContentLoaded', function () {
    // تهيئة الواجهة
    initializeInterface();

    // إعداد معالج رفع الملفات
    setupFileUpload();

    // إعداد الرسائل المؤقتة
    setupMessages();
});

function initializeInterface() {
    // إضافة تأثيرات تفاعلية للعناصر
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function () {
            this.style.transform = 'translateY(-2px)';
        });

        button.addEventListener('mouseleave', function () {
            this.style.transform = 'translateY(0)';
        });
    });

    // إضافة تأثيرات للبطاقات
    const cards = document.querySelectorAll('.upload-card, .info-card, .schedule-table-container, .constraints-card, .summary-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.2)';
        });

        card.addEventListener('mouseleave', function () {
            this.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
        });
    });
}

function setupFileUpload() {
    const fileInput = document.getElementById('file');
    const fileLabel = document.querySelector('.file-label');
    const fileText = document.querySelector('.file-text');

    if (fileInput && fileLabel && fileText) {
        fileInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                const fileSize = (this.files[0].size / 1024 / 1024).toFixed(2);

                fileText.innerHTML = `
                    <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                    <span>تم اختيار: ${fileName}</span>
                    <small style="display: block; margin-top: 0.5rem; color: var(--text-muted);">
                        الحجم: ${fileSize} ميجابايت
                    </small>
                `;

                fileLabel.style.borderColor = 'var(--success-color)';
                fileLabel.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
            }
        });

        // إضافة تأثير السحب والإفلات
        fileLabel.addEventListener('dragover', function (e) {
            e.preventDefault();
            this.style.borderColor = 'var(--primary-color)';
            this.style.backgroundColor = 'var(--bg-hover)';
        });

        fileLabel.addEventListener('dragleave', function (e) {
            e.preventDefault();
            this.style.borderColor = 'var(--border-color)';
            this.style.backgroundColor = 'var(--bg-secondary)';
        });

        fileLabel.addEventListener('drop', function (e) {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }
}

function setupMessages() {
    // إخفاء الرسائل تلقائياً بعد 5 ثوان
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
}

// وظائف مساعدة
function showLoading(element) {
    if (element) {
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري المعالجة...';
        element.disabled = true;
    }
}

function hideLoading(element, originalText) {
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 بايت';

    const k = 1024;
    const sizes = ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function validateFile(file) {
    const allowedTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
        'application/vnd.ms-excel' // .xls
    ];

    const maxSize = 10 * 1024 * 1024; // 10 MB

    if (!allowedTypes.includes(file.type)) {
        return {
            valid: false,
            message: 'نوع الملف غير مدعوم. يرجى رفع ملف Excel (.xlsx أو .xls)'
        };
    }

    if (file.size > maxSize) {
        return {
            valid: false,
            message: 'حجم الملف كبير جداً. الحد الأقصى هو 10 ميجابايت'
        };
    }

    return {
        valid: true,
        message: 'الملف صحيح'
    };
}

// إضافة تأثيرات إضافية للجدول
function enhanceTable() {
    const table = document.querySelector('.schedule-table');
    if (table) {
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach((row, index) => {
            row.style.animationDelay = `${index * 0.1}s`;
            row.classList.add('fade-in');
        });
    }
}

// إضافة CSS للرسوم المتحركة
const style = document.createElement('style');
style.textContent = `
    .fade-in {
        animation: fadeInUp 0.6s ease-out forwards;
        opacity: 0;
        transform: translateY(20px);
    }
    
    @keyframes fadeInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .btn:active {
        transform: translateY(0) scale(0.98);
    }
    
    .file-label:active {
        transform: scale(0.98);
    }
`;
document.head.appendChild(style);

// تشغيل تحسينات إضافية عند تحميل الصفحة
window.addEventListener('load', function () {
    enhanceTable();
});
