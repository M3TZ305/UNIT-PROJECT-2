# تَليد — التشغيل والتسليم

موقع Django عن ثقافات المدن السعودية. العربية افتراضيًا، والإنجليزية متاحة من زر اللغة. اسم المشروع البرمجي `config` والتطبيق `main`؛ اسم الموقع تَليد / Taleed.

## التشغيل لأول مرة

افتح Terminal داخل مجلد المشروع في VS Code:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py sync_geography
.\.venv\Scripts\python.exe manage.py compile_translations
.\.venv\Scripts\python.exe manage.py runserver
```

افتح http://127.0.0.1:8000/ . على جهازك المجهز يكفي أمر التشغيل الأخير. لا يلزم تفعيل البيئة إذا استُخدم مسار Python المباشر. إذا كان المنفذ مشغولًا أضف `8001` لأمر التشغيل.

قاعدة SQLite والبيئة مستثناتان من Git؛ لذلك لا تتخطَّ migrate وsync_geography عند تنزيل المشروع على جهاز جديد. لا تحتاج Pillow لتشغيل الموقع؛ استُخدمت أداة ضغط في مرحلة إعداد الصور فقط.

## الصفحات الفعلية

الموقع يحوي ٥٨ صفحة محتوى مميزة، مع إعادة استخدام القوالب:

- الرئيسية `/`، واكتشف المدن `/cities/`، وعن تليد `/about/`.
- ٣ موضوعات: `/culture/architecture/` و`/culture/crafts/` و`/culture/food/`.
- ١٣ مدينة رئيسية تمثل المناطق الإدارية، و٣ صفحات مدن إضافية محفوظة من النسخة السابقة.
- ٣٥ محافظة مختارة، بمحافظتين أو ثلاث لكل منطقة: `/cities/<capital>/governorates/<slug>/`.

تبدأ قائمة المدن بالمدينة المنورة. المحافظات تتبع المنطقة إداريًا؛ المدينة الرئيسية بوابة لاستكشافها. بعض الروابط القديمة للمدن تحول العرض إلى المحافظة نفسها، ولا تُحسب محتوى جديدًا.

## أين طُبقت دروس الوحدة؟

| الدرس | موضع التطبيق |
|---|---|
| Project / App | `config` و`main` |
| Models وMVT | City وGovernorate في models.py، مع SQLite وDjango admin |
| Views | استقبال الطلب، القراءة من Models وJSON، ثم اختيار القالب |
| Templates وInheritance | base.html وقوالب main وincludes |
| Static | CSS وJavaScript والخطوط والصور وfavicon |
| URL Mapping وResolving | الروابط المسماة ووسم url وreverse |
| Path Parameters | slug للمدينة والمحافظة والموضوع |
| Query Parameters | q وregion وprovince وcategory وsaved |
| Cookies | theme وsaved_cities وsite_language، مع HttpOnly وSameSite |
| JSON | المحتوى التحريري منفصل عن القوالب ومنطق الطلب |
| English | gettext في locale/en، وترجمة حقول المحتوى وقت العرض |

مثال للمناقشة: طلب صفحة المدينة يمر من URL إلى View، ثم يُجلب فهرس المكان من Model وتفاصيله من JSON، ويُعرض بقالب مشترك يرث base.html. تغيير slug يغيّر المحتوى دون إنشاء قالب جديد.

## تعديل المحتوى والترجمة

- `data/geography.json`: ترتيب المدن وتبعية المحافظات والروابط القديمة.
- `data/cities.json` و`governorates.json`: التعريف والفهرسة والتاريخ.
- `data/place_profiles.json`: المعالم التاريخية، مصادرها وحكاياتها.
- `data/local_culture.json`: الزي الرجالي والنسائي والأطباق والثمار لكل مكان.
- `data/media.json`: الصور، أصحابها، تراخيصها والنسخ المحلية.
- `data/culture.json`: موضوعات العمارة والحرف والمذاق.
- `locale/en/LC_MESSAGES/django.po`: النصوص الإنجليزية. بعد التعديل شغّل compile_translations وأعد تشغيل الخادم.

عند تغيير فهرس المدن أو المحافظات شغّل sync_geography. تعديل SQLite من admin وحده لا يستبدل مصدر المحتوى التحريري في JSON. تحرير النص العربي يستلزم مراجعة ترجمته المقابلة في PO؛ لا توجد خدمة ترجمة خارجية أثناء استخدام الموقع.

## دقة المعلومات والصور

الأطباق والثمار تحتاج مصدرًا يربطها بالمكان نفسه، ولا تُورث من المنطقة. عند نقص الدليل تبقى المائدة ظاهرة مع حالة توثيق واضحة.

الأزياء المحلية مقدّمة عند وجود دليل مستقل؛ وعند غيابه سمح صاحب المشروع بعرض مثال إقليمي أو سعودي مشترك مع بيان نطاقه صراحةً داخل البطاقة. لا تُنسب الأزياء المشتركة حصريًا للمحافظة.

المعالم تاريخية وتراثية داخل النطاق المحدد، بحد أقصى خمسة؛ يُسمح بعدد أقل إذا لم يتوفر توثيق كافٍ. ما زالت بعض الأماكن بلا أطباق أو ثمار مثبتة، وبعض المعالم بلا صورة؛ لا يثبت الاختبار الآلي صحة المعلومات التاريخية بنسبة مطلقة.

الرسوم التعريفية مولّدة وتُميّز عن الصور الفوتوغرافية. تبقى مصادر الصور وحقوقها محفوظة. الصور المضغوطة تحتفظ بالأبعاد والشفافية، وتتوفر نسخة احتياطية خارج المشروع من حالة ما قبل التنظيف.

## تجهيز بونس الصور — Cloudinary

الرفع غير منفذ بعد؛ يلزم حساب Cloudinary يخص صاحب المشروع. افتح https://cloudinary.com/ وأنشئ حساب Image & Video API، ثم احصل من لوحة الحساب على Cloud name وAPI key وAPI secret. لا ترسل API secret في المحادثة ولا تضعه في Git.

تجهيز الحزمة دون حساب ودون اتصال:

```powershell
.\.venv\Scripts\python.exe manage.py export_media
.\.venv\Scripts\python.exe manage.py upload_cdn
```

ينشئ الأمر الأول `release/media-upload.zip` مع ملفات الحقوق، و`release/cdn-upload.json` مع بصمات الملفات. الأمر الثاني معاينة فقط، ولا يرفع شيئًا. الحزمة وبيانات الحساب مستثناة من Git.

بعد إعداد الحساب، اضبط المتغيرات في جلسة Terminal الخاصة بك:

```powershell
$env:CLOUDINARY_CLOUD_NAME = "your-cloud-name"
$env:CLOUDINARY_API_KEY = "your-api-key"
$env:CLOUDINARY_API_SECRET = "your-private-api-secret"
.\.venv\Scripts\python.exe manage.py upload_cdn --upload
```

لا تنفذ سطور البيانات أمام مشاركة شاشة عامة. يمكن إضافة `--limit 3` لرفع ثلاث صور أولًا. الأمر يحفظ الروابط في `data/cdn_manifest.json` ويتجاوز الملفات التي رُفعت ولم تتغير. الصور تتجه إلى CDN عند تطابق بصمتها، مع بقاء النسخة المحلية بديلًا عند التعذر. تعديل صورة يستلزم تصدير الحزمة ورفع النسخة الجديدة. ملف manifest يحوي روابط عامة وبصمات فقط، ويمكن إرفاقه بالمشروع.

توثيق Cloudinary: https://cloudinary.com/documentation/upload_images

## النشر على الإنترنت

التشغيل الافتراضي تطوير محلي. إعدادات النشر تقرأ متغيرات البيئة؛ `.env.example` نموذج للأسماء فقط، ولا يُقرأ تلقائيًا. لا تستخدم مفتاح التطوير في النشر.

يلزم إعداد DJANGO_DEBUG=false ومفتاح عشوائي خاص وDJANGO_ALLOWED_HOSTS وDJANGO_CSRF_TRUSTED_ORIGINS للنطاق الفعلي. استعمل خادم WSGI/ASGI خلف HTTPS وخدمة للملفات الثابتة؛ runserver للعرض المحلي. لا تفعل DJANGO_TRUST_PROXY إلا خلف وكيل موثوق تملكه. مدة HSTS قابلة للضبط ويجب مراجعتها للنطاق الفعلي.

```powershell
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check --deploy
```

شغّل فحص النشر ببيئة النشر الفعلية. ملفات staticfiles ناتج توليد ومستثناة من Git. توثيق Django: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

## التحقق قبل التسليم

```powershell
.\.venv\Scripts\python.exe manage.py test main
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

راجع بصريًا العربية والإنجليزية والوضعين عند عرض ٣٧٥ و٧٦٨ و١٤٤٠ بكسل، وجرّب اللغة والحفظ والبحث ومعرض الصور والفيديو. يحتوي الموقع على تقليل الحركة ودعم لوحة المفاتيح وRTL/LTR. فحص القوالب والاختبارات لا يعادل اختبار المتصفح البصري، والفيديوهات تحتاج الإنترنت وقد تتأثر بقيود الناشر.

## شرح مختصر أثناء المناقشة

1. الرئيسية تعرض الفكرة، ثم المدن والمحافظات بمحتوى مستقل وقوالب مشتركة.
2. نموذج City وGovernorate فهرس حقيقي في SQLite، والتفاصيل التحريرية من JSON.
3. slug مثال Path Parameter، والبحث والفلترة مثال Query Parameters.
4. اللغة والألوان والحفظ تفضيلات محفوظة بالكوكيز، وتغييرات POST محمية بـCSRF.
5. الصور لها مصادر وتراخيص؛ الرسوم التصورية واضحة، والرفع السحابي قابل للتشغيل بعد إعداد الحساب.
6. اعرض الاختبارات ثم نفذ تبديل اللغة والوضع والحفظ والبحث أمام الدكتور.

## صيانة التصميم والصور

- ملفات التنسيق المشتركة: `foundation.css` للأساس والخطوط، `reading.css` للقراءة والتكوين، و`interface.css` للتنقل والمكونات والمسافات. ترتيب تحميلها مقصود وتأتي تنسيقات الصفحة بينها.
- أقسام الحِرف والعمارة والأزياء والمائدة قابلة للفتح دون JavaScript. الروابط المباشرة تفتح القسم المطلوب تلقائيًا عند تفعيل JavaScript.
- بيانات المجموعات تُجمع من بيانات الأماكن؛ لا توجد نسخة ثانية من عناصر الحِرف والمائدة في `culture.json`.
- الصور الكاملة باقية للتكبير، والنسخ الأخف مسجّلة في `data/responsive_images.json`. لإعادة تجهيزها بعد إضافة صور محلية: `.venv\Scripts\python.exe manage.py prepare_images`. يتطلب أمر التجهيز Pillow؛ عرض الموقع لا يتطلبها.
- حزمة رفع الصور القديمة حُذفت؛ أعد توليدها بأمر `export_media` عندما يحين وقت الرفع.
