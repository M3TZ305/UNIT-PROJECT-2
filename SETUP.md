# ملامح — دليل التشغيل والمناقشة

المشروع داخل فورك UNIT-PROJECT-2. تعليمات الدكتور في README.md وملف .gitignore محفوظان كما هما.

## تشغيل النسخة الموجودة

افتح Terminal داخل مجلد الفورك في VS Code:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

ثم افتح http://127.0.0.1:8000/ . الأمر يستخدم Python من البيئة مباشرة دون الحاجة إلى تفعيلها.

للتفعيل اختياريًا:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

إذا منع PowerShell التفعيل، استخدم أمر التشغيل المباشر؛ لا تحتاج إلى تغيير Execution Policy. إذا كان المنفذ مشغولًا استخدم `manage.py runserver 8001`.

## تجهيز المشروع بعد تنزيله من GitHub

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py sync_cities
.\.venv\Scripts\python.exe manage.py runserver
```

النسخة المحلية جهّزت بالفعل. قاعدة SQLite والبيئة الافتراضية مستثناتان من Git، ولذلك يجب تنفيذ migrate وsync_cities على أي جهاز جديد.

## الصفحات — 10 صفحات

- `/`: الرئيسية الافتتاحية، دون قائمة المدن.
- `/cities/`: استكشاف وبحث وفلترة وحكايات محفوظة.
- `/cities/jeddah/`, `/cities/riyadh/`, `/cities/abha/`, `/cities/hail/`, `/cities/hofuf/`, `/cities/alula/`: ست صفحات بيانات مختلفة بقالب واحد.
- `/about/`: فكرة المشروع وسياسة التفضيلات.
- `/sources/`: المصادر ونسبة الصور وتراخيصها وروابط الفيديو.

## أين طبّقنا الدروس؟

| الموضوع | التطبيق |
|---|---|
| Project / App | config للإعدادات، وmain لمنطق الموقع |
| Model | City في main/models.py؛ جدول حقيقي في SQLite، ومسجّل في Django admin |
| View | main/views.py يستقبل الطلب ويختار البيانات والقالب |
| Template | قوالب HTML في templates/main |
| Template Inheritance | كل الصفحات ترث base.html، وincludes للصورة والحفظ |
| Static | CSS وJavaScript وfavicon والصور الاحتياطية في static |
| URL Mapping | config/urls.py يضم main.urls، وروابط مسماة داخل app_name |
| Resolving URLs | وسم url في القوالب وreverse في Python |
| Path Parameters | slug في cities/<slug:slug>/ وفي حفظ المدينة |
| Query Parameters | q وregion وcategory وsaved في صفحة المدن |
| Cookies | theme لوضع الألوان وsaved_cities للمدن المحفوظة؛ كلاهما HttpOnly وSameSite=Lax |
| JSON | cities.json للحكايات والمعارض والروابط، وmedia.json لروابط الصور والحقوق |

مثال الدورة: `/cities/jeddah/` ← URL يمرر slug ← View يجد City في قاعدة البيانات ← City.data يقرأ التفاصيل من JSON ← القالب المشترك يرث base.html ويعرضها.

## تعديل المحتوى

غيّر data/cities.json. النصوص والمعارض تقرأ النسخة الجديدة تلقائيًا. إذا عدلت اسم المدينة أو وصف البحث أو منطقتها أو تصنيفاتها شغّل:

```powershell
.\.venv\Scripts\python.exe manage.py sync_cities
```

الأمر يحدّث الفهرس دون تكرار المدن. القالب الواحد يدعم إضافة مدينة أخرى، بعد توفير حقولها ووسائطها في JSON ثم المزامنة. تعديل الفهرس من admin وحده لا يغيّر المحتوى التحريري في JSON؛ المصدر الأساسي هو JSON.

## الحركة والتفاعل

- كشف الصور والعناوين عند الدخول، وظهور أقسام أثناء التمرير.
- عمق خفيف لصورة الرئيسية مع المؤشر، وانتقالات بصرية يدعمها المتصفح.
- تغيير الوضع الليلي دون إعادة تحميل، مع حفظه في Cookie.
- حفظ المدن، مع بديل يعمل دون JavaScript عبر النماذج.
- معرض تكبير يدعم الأسهم وEscape والإغلاق.
- فتح فيديو YouTube عند الطلب فقط، وإيقافه بإزالة iframe عند الإغلاق.
- قائمة مناسبة للجوال، وروابط فصول تتابع موضع القراءة.
- احترام تفضيل تقليل الحركة في النظام، وتركيز لوحة المفاتيح، وRTL.

## الميديا وCDN

روابط الصور موجودة في media.json وتأتي من خدمة Wikimedia الخارجية. الفيديوهات مضمّنة من YouTube عبر youtube-nocookie. هذه ملفات مستضافة أصلًا لدى أصحابها؛ لم نرفع ميديا إلى حساب سحابي خاص بك ولم ننشئ حسابًا أو اشتراكًا. إذا اشترط الدكتور الرفع إلى مساحة تملكها أنت، يبقى هذا إجراء منفصل باستخدام حسابك، ثم نبدل الروابط في JSON. لا نضمن البونس بناءً على استخدام روابط خارجية فقط.

الصور لها نسخ محلية احتياطية، وتعمل عند فشل المصدر الخارجي. بيانات الحقوق والتراخيص لكل صورة في صفحة المصادر. استخدمت الصور مع قص داخل العرض، دون ادعاء أن الصور الإقليمية تقع داخل المدينة؛ يظهر موقعها في التعليق.

الفيديوهات والخطوط تحتاج إلى إنترنت. تعطيل تضمين فيديو من ناشره أو تقييده حسب البلد احتمال خارج سيطرة المشروع؛ لكل فيلم رابط مشاهدة مباشر أيضًا.

## التحقق

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

تغطي الاختبارات الصفحات العشر، القالب المشترك، البحث العربي دون تأثر بالتشكيل، جمع الفلاتر، الحفظ والإزالة، cookies غير الصالحة، CSRF، منع إعادة التوجيه لمواقع خارجية، 404، اكتمال الميديا ومزامنة البيانات دون تكرار.

## قبل التسليم

- لا ترفع .venv أو db.sqlite3؛ .gitignore الأصلي يستثنيهما.
- ارفع ملفات المصدر وrequirements.txt وملف migration وdata وstatic وtemplates.
- config/settings.py للتطوير المحلي؛ DEBUG=True والخادم runserver ليسا إعداد نشر إنتاجي.
- المشروع لم يُنشر على الإنترنت، ولم يُعمل commit أو push نيابة عنك.
- راجع المحتوى والمصادر بنفسك حتى تشرح اختياراتك للدكتور.
