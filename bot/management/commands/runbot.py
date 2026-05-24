from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.error import TelegramError

from logistics.models import Driver, Load, TelegramProfile, UZBEKISTAN_REGIONS

REGISTER_ROLE, REGISTER_PHONE, REGISTER_TRUCK = range(3)
(
    LOAD_FROM,
    LOAD_TO,
    LOAD_VOLUME,
    LOAD_WEIGHT,
    LOAD_TYPE,
    LOAD_VEHICLE,
    LOAD_PRICE,
    LOAD_PHONE,
    LOAD_NOTE,
) = range(10, 19)

REGION_COORDS = {
    'toshkent_shahri': (41.3111, 69.2797),
    'toshkent': (41.0, 69.0),
    'andijon': (40.7821, 72.3442),
    'fargona': (40.3894, 71.7848),
    'namangan': (41.0011, 71.6683),
    'sirdaryo': (40.8436, 68.6617),
    'jizzax': (40.1158, 67.8422),
    'samarqand': (39.6270, 66.9750),
    'qashqadaryo': (38.8610, 65.7847),
    'surxondaryo': (37.9409, 67.5709),
    'buxoro': (39.7670, 64.4230),
    'navoiy': (40.0844, 65.3792),
    'xorazm': (41.3565, 60.8567),
    'qoraqalpogiston': (42.4619, 59.6166),
}
REGION_LABELS = dict(UZBEKISTAN_REGIONS)
REGION_BY_LABEL = {label: key for key, label in UZBEKISTAN_REGIONS}


def role_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('Yuk egasi', callback_data='role:cargo_owner'),
            InlineKeyboardButton('Haydovchi', callback_data='role:driver'),
        ],
        [InlineKeyboardButton('Logist', callback_data='role:logist')],
    ])


def region_keyboard():
    rows = []
    labels = list(REGION_BY_LABEL.keys())
    for index in range(0, len(labels), 2):
        rows.append(labels[index:index + 2])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton('Telefon raqamni yuborish', request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_keyboard(profile=None):
    rows = [['Aktiv yuklar', 'Menga yaqin yuklar']]
    if profile and profile.role in ['cargo_owner', 'logist']:
        rows.insert(0, ['Yuk joylash', 'Mening yuklarim'])
    rows.append(['Ro‘yxatdan o‘tish'])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def nearest_region(latitude, longitude):
    best_key = None
    best_distance = None
    for key, (region_lat, region_lon) in REGION_COORDS.items():
        distance = (float(latitude) - region_lat) ** 2 + (float(longitude) - region_lon) ** 2
        if best_distance is None or distance < best_distance:
            best_key = key
            best_distance = distance
    return best_key


def format_load(load, include_private=False):
    price = load.price_text or ('Kelishiladi' if load.price_type == 'negotiable' else f'{load.client_price} so‘m')
    lines = [
        f"📦 {load.title}",
        f"📍 Qayerdan: {load.get_from_region_display()}",
        f"🏁 Qayerga: {load.get_to_region_display()}",
        f"📐 Hajm: {load.cargo_volume or '-'}",
        f"⚖️ Og‘irlik: {load.weight_text or load.weight_tons or '-'}",
        f"🚚 Yuk turi: {load.cargo_type or '-'}",
        f"🚛 Avtomashina turi: {load.vehicle_type or '-'}",
        f"💰 Narx: {price}",
    ]
    if load.notes:
        lines.append(f"📝 Izoh: {load.notes}")
    if include_private:
        if load.contact_phone:
            lines.append(f"☎️ Telefon: {load.contact_phone}")
        if load.owner_contact_info:
            lines.append(f"👤 Yuk egasi/logist: {load.owner_contact_info}")
        if load.logist_contact_info:
            lines.append(f"🧭 Logist: {load.logist_contact_info}")
    return '\n'.join(lines)


def owner_load_keyboard(load):
    buttons = []
    if load.status in ['new', 'assigned', 'in_transit']:
        buttons.append([InlineKeyboardButton('❌ Yukni bekor qilish', callback_data=f'cancel_load:{load.id}')])
    return InlineKeyboardMarkup(buttons) if buttons else None


@sync_to_async
def get_profile(user):
    return TelegramProfile.objects.filter(telegram_id=user.id, is_active=True).first()


@sync_to_async
def save_profile(user, role, phone='', truck_number=''):
    profile, _ = TelegramProfile.objects.update_or_create(
        telegram_id=user.id,
        defaults={
            'username': user.username or '',
            'full_name': user.full_name,
            'phone': phone,
            'role': role,
            'truck_number': truck_number,
            'is_active': True,
        },
    )
    if role == 'driver':
        driver, _ = Driver.objects.update_or_create(
            telegram_id=user.id,
            defaults={
                'full_name': user.full_name,
                'phone': phone,
                'truck_number': truck_number,
                'status': 'approved',
                'is_active': True,
            },
        )
        profile.driver = driver
        profile.save(update_fields=['driver'])
    return profile


@sync_to_async
def create_load_from_context(user, data):
    profile = TelegramProfile.objects.get(telegram_id=user.id)
    price_input = data['price'].strip()
    price_type = 'negotiable' if price_input.lower() in ['kelishiladi', 'kelishish', 'kelishamiz'] else 'fixed'
    client_price = Decimal('0')
    if price_type == 'fixed':
        try:
            client_price = Decimal(price_input.replace(' ', '').replace(',', '.'))
        except InvalidOperation:
            price_type = 'negotiable'

    load = Load.objects.create(
        title=f"{REGION_LABELS[data['from_region']]} -> {REGION_LABELS[data['to_region']]}",
        created_by_profile=profile,
        from_region=data['from_region'],
        to_region=data['to_region'],
        from_city=REGION_LABELS[data['from_region']],
        to_city=REGION_LABELS[data['to_region']],
        cargo_volume=data['volume'],
        weight_text=data['weight'],
        cargo_type=data['cargo_type'],
        vehicle_type=data['vehicle_type'],
        price_type=price_type,
        price_text='Kelishiladi' if price_type == 'negotiable' else f'{client_price} so‘m',
        client_price=client_price,
        contact_phone=data['phone'],
        notes=data.get('note', ''),
        owner_contact_info=profile.contact_line,
        logist_contact_info=profile.contact_line if profile.role == 'logist' else '',
    )
    return load


@sync_to_async
def mark_announcement(load_id, chat_id, message_id):
    Load.objects.filter(id=load_id).update(
        announcement_chat_id=str(chat_id),
        announcement_message_id=message_id,
    )


@sync_to_async
def get_active_loads(region=None):
    queryset = Load.objects.filter(status='new').order_by('-created_at')
    if region:
        queryset = queryset.filter(from_region=region)
    return list(queryset[:10])


@sync_to_async
def get_owner_loads(user):
    profile = TelegramProfile.objects.filter(
        telegram_id=user.id,
        role__in=['cargo_owner', 'logist'],
        is_active=True,
    ).first()
    if not profile:
        return 'not_allowed', []

    loads = list(
        Load.objects.filter(created_by_profile=profile)
        .exclude(status='cancelled')
        .order_by('-created_at')[:10]
    )
    return 'ok', loads


@sync_to_async
def accept_load(load_id, user):
    with transaction.atomic():
        profile = TelegramProfile.objects.select_for_update().filter(
            telegram_id=user.id,
            role='driver',
            is_active=True,
        ).first()
        if not profile:
            return 'not_registered', None

        load = Load.objects.select_for_update().filter(id=load_id).first()
        if not load:
            return 'not_found', None
        if load.status != 'new' or load.assigned_driver_profile_id:
            return 'already_taken', load

        load.assigned_driver_profile = profile
        load.driver = profile.driver
        load.status = 'assigned'
        load.save(update_fields=['assigned_driver_profile', 'driver', 'status', 'updated_at'])
        return 'accepted', load


@sync_to_async
def cancel_owner_load(load_id, user):
    with transaction.atomic():
        profile = TelegramProfile.objects.select_for_update().filter(
            telegram_id=user.id,
            role__in=['cargo_owner', 'logist'],
            is_active=True,
        ).first()
        if not profile:
            return 'not_allowed', None

        load = Load.objects.select_for_update().filter(id=load_id, created_by_profile=profile).first()
        if not load:
            return 'not_found', None
        if load.status == 'cancelled':
            return 'already_cancelled', load
        if load.status == 'delivered':
            return 'delivered', load

        load.status = 'cancelled'
        load.save(update_fields=['status', 'updated_at'])
        return 'cancelled', load


@sync_to_async
def update_driver_location(user, latitude, longitude):
    region = nearest_region(latitude, longitude)
    profile = TelegramProfile.objects.filter(telegram_id=user.id, role='driver').first()
    if not profile:
        return None
    profile.last_latitude = latitude
    profile.last_longitude = longitude
    profile.current_region = region
    profile.save(update_fields=['last_latitude', 'last_longitude', 'current_region', 'updated_at'])
    return profile


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = await get_profile(update.effective_user)
    text = (
        "UZT Cargo botiga xush kelibsiz.\n\n"
        "Yuk egasi yoki logist yuk joylaydi, haydovchi esa e’londagi tugma orqali yukni qabul qiladi."
    )
    await update.message.reply_text(text, reply_markup=main_keyboard(profile))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/register - ro‘yxatdan o‘tish\n"
        "/newload - yuk joylash\n"
        "/myloads - mening yuklarim va bekor qilish\n"
        "/loads - aktiv yuklar\n"
        "/nearloads - menga yaqin yuklar\n"
        "/cancel - jarayonni bekor qilish"
    )


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Rolingizni tanlang:', reply_markup=role_keyboard())
    return REGISTER_ROLE


async def register_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['register_role'] = query.data.split(':', 1)[1]
    await query.message.reply_text('Telefon raqamingizni yuboring:', reply_markup=phone_keyboard())
    return REGISTER_PHONE


async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data['register_phone'] = phone
    if context.user_data['register_role'] == 'driver':
        await update.message.reply_text('Mashina raqamini kiriting:', reply_markup=ReplyKeyboardRemove())
        return REGISTER_TRUCK

    profile = await save_profile(update.effective_user, context.user_data['register_role'], phone)
    await update.message.reply_text(
        f"Ro‘yxatdan o‘tdingiz: {profile.get_role_display()}",
        reply_markup=main_keyboard(profile),
    )
    return ConversationHandler.END


async def register_truck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = await save_profile(
        update.effective_user,
        context.user_data['register_role'],
        context.user_data['register_phone'],
        update.message.text,
    )
    await update.message.reply_text(
        f"Ro‘yxatdan o‘tdingiz: {profile.get_role_display()}",
        reply_markup=main_keyboard(profile),
    )
    return ConversationHandler.END


async def newload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = await get_profile(update.effective_user)
    if not profile:
        await update.message.reply_text('Avval /register orqali ro‘yxatdan o‘ting.')
        return ConversationHandler.END
    if profile.role not in ['cargo_owner', 'logist']:
        await update.message.reply_text('Yukni faqat yuk egasi yoki logist joylay oladi.')
        return ConversationHandler.END

    context.user_data['new_load'] = {}
    await update.message.reply_text('Qayerdan? Viloyatni tanlang:', reply_markup=region_keyboard())
    return LOAD_FROM


async def load_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    region = REGION_BY_LABEL.get(update.message.text)
    if not region:
        await update.message.reply_text('Ro‘yxatdan viloyat tanlang.', reply_markup=region_keyboard())
        return LOAD_FROM
    context.user_data['new_load']['from_region'] = region
    await update.message.reply_text('Qayerga? Viloyatni tanlang:', reply_markup=region_keyboard())
    return LOAD_TO


async def load_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    region = REGION_BY_LABEL.get(update.message.text)
    if not region:
        await update.message.reply_text('Ro‘yxatdan viloyat tanlang.', reply_markup=region_keyboard())
        return LOAD_TO
    context.user_data['new_load']['to_region'] = region
    await update.message.reply_text('Yuk hajmini kiriting. Masalan: 82 m3', reply_markup=ReplyKeyboardRemove())
    return LOAD_VOLUME


async def load_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_load']['volume'] = update.message.text
    await update.message.reply_text('Yuk og‘irligini kiriting. Masalan: 20 tonna')
    return LOAD_WEIGHT


async def load_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_load']['weight'] = update.message.text
    await update.message.reply_text('Yuk turini kiriting. Masalan: mebel, oziq-ovqat, qurilish materiali')
    return LOAD_TYPE


async def load_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_load']['cargo_type'] = update.message.text
    await update.message.reply_text('Kerakli avtomashina turini kiriting. Masalan: fura, tent, izoterm, refrijerator, bortli')
    return LOAD_VEHICLE


async def load_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_load']['vehicle_type'] = update.message.text
    await update.message.reply_text("Yuk narxini kiriting. Summa yozing yoki 'kelishiladi' deb yuboring.")
    return LOAD_PRICE


async def load_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_load']['price'] = update.message.text
    await update.message.reply_text('Telefon raqamni yuboring:', reply_markup=phone_keyboard())
    return LOAD_PHONE


async def load_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data['new_load']['phone'] = phone
    await update.message.reply_text("Izoh yozing yoki '-' yuboring.", reply_markup=ReplyKeyboardRemove())
    return LOAD_NOTE


async def load_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    context.user_data['new_load']['note'] = '' if note == '-' else note
    load = await create_load_from_context(update.effective_user, context.user_data['new_load'])

    await update.message.reply_text('Yuk saqlandi. E’lon chiqarilmoqda...', reply_markup=main_keyboard(await get_profile(update.effective_user)))
    published, error_text = await publish_load(context, load)
    if published:
        await update.message.reply_text('Yuk kanalga chiqarildi.')
    else:
        await update.message.reply_text(f'Yuk saqlandi, lekin kanalga chiqarilmadi: {error_text}')
    return ConversationHandler.END


async def publish_load(context: ContextTypes.DEFAULT_TYPE, load):
    text = format_load(load)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Qabul qilish', callback_data=f'accept:{load.id}')]
    ])

    chat_id = settings.TELEGRAM_ANNOUNCEMENT_CHAT_ID
    if not chat_id:
        return False, 'TELEGRAM_ANNOUNCEMENT_CHAT_ID sozlanmagan'

    try:
        message = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    except TelegramError as exc:
        return False, str(exc)

    await mark_announcement(load.id, message.chat_id, message.message_id)
    return True, ''


async def loads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loads = await get_active_loads()
    if not loads:
        await update.message.reply_text("Hozircha aktiv yuklar yo‘q.")
        return

    for load in loads:
        await update.message.reply_text(
            format_load(load),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('✅ Qabul qilish', callback_data=f'accept:{load.id}')]]),
        )


async def myloads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status, loads = await get_owner_loads(update.effective_user)
    if status == 'not_allowed':
        await update.message.reply_text('Bu bo‘lim faqat yuk egasi va logistlar uchun.')
        return
    if not loads:
        await update.message.reply_text('Siz joylagan aktiv yuklar yo‘q.')
        return

    for load in loads:
        await update.message.reply_text(
            format_load(load),
            reply_markup=owner_load_keyboard(load),
        )


async def nearloads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = await get_profile(update.effective_user)
    if not profile or profile.role != 'driver':
        await update.message.reply_text('Yaqin yuklarni ko‘rish uchun haydovchi sifatida /register qiling.')
        return

    button = KeyboardButton('Lokatsiyani yuborish', request_location=True)
    await update.message.reply_text(
        'Lokatsiyangizni yuboring, sizga yaqin yuklarni ko‘rsataman.',
        reply_markup=ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True),
    )


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    profile = await update_driver_location(update.effective_user, location.latitude, location.longitude)
    if not profile:
        await update.message.reply_text('Avval haydovchi sifatida /register qiling.')
        return

    loads = await get_active_loads(profile.current_region)
    region_name = profile.get_current_region_display()
    if not loads:
        await update.message.reply_text(f'{region_name} atrofida aktiv yuk topilmadi.', reply_markup=main_keyboard(profile))
        return

    await update.message.reply_text(f'{region_name} atrofidagi yuklar:', reply_markup=main_keyboard(profile))
    for load in loads:
        await update.message.reply_text(
            format_load(load),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('✅ Qabul qilish', callback_data=f'accept:{load.id}')]]),
        )


async def accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    load_id = int(query.data.split(':', 1)[1])
    status, load = await accept_load(load_id, query.from_user)

    if status == 'not_registered':
        await query.answer('Avval botdan haydovchi sifatida ro‘yxatdan o‘ting: /register', show_alert=True)
        return
    if status == 'not_found':
        await query.answer('Yuk topilmadi.', show_alert=True)
        return
    if status == 'already_taken':
        await query.answer('Yuk qabul qilingan.', show_alert=True)
        return

    await query.answer('Yuk sizga biriktirildi.', show_alert=True)
    accepted_text = format_load(load) + "\n\n✅ Yuk qabul qilindi."
    try:
        await query.edit_message_text(accepted_text)
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Yuk sizga biriktirildi.\n\n" + format_load(load, include_private=True),
    )


async def cancel_load_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    load_id = int(query.data.split(':', 1)[1])
    status, load = await cancel_owner_load(load_id, query.from_user)

    if status == 'not_allowed':
        await query.answer('Bu amal faqat yuk egasi yoki logist uchun.', show_alert=True)
        return
    if status == 'not_found':
        await query.answer('Bu yuk topilmadi yoki sizga tegishli emas.', show_alert=True)
        return
    if status == 'already_cancelled':
        await query.answer('Bu yuk oldin bekor qilingan.', show_alert=True)
        return
    if status == 'delivered':
        await query.answer('Yetkazilgan yukni bekor qilib bo‘lmaydi.', show_alert=True)
        return

    cancelled_text = format_load(load) + "\n\n❌ Yuk bekor qilindi."
    await query.answer('Yuk bekor qilindi.', show_alert=True)
    try:
        await query.edit_message_text(cancelled_text)
    except TelegramError:
        pass

    if load.announcement_chat_id and load.announcement_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=load.announcement_chat_id,
                message_id=load.announcement_message_id,
                text=cancelled_text,
            )
        except TelegramError:
            pass

    if load.assigned_driver_profile:
        try:
            await context.bot.send_message(
                chat_id=load.assigned_driver_profile.telegram_id,
                text='Sizga biriktirilgan yuk bekor qilindi.\n\n' + format_load(load),
            )
        except TelegramError:
            pass


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Ro‘yxatdan o‘tish':
        return await register_start(update, context)
    if text == 'Yuk joylash':
        return await newload_start(update, context)
    if text == 'Aktiv yuklar':
        return await loads_command(update, context)
    if text == 'Menga yaqin yuklar':
        return await nearloads_command(update, context)
    if text == 'Mening yuklarim':
        return await myloads_command(update, context)
    await update.message.reply_text('Buyruq tanlang yoki /help ni bosing.')


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Bekor qilindi.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


class Command(BaseCommand):
    help = 'Run UZT Cargo Telegram bot'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN .env ichida berilmagan')

        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        register_conv = ConversationHandler(
            entry_points=[
                CommandHandler('register', register_start),
                MessageHandler(filters.Regex('^Ro‘yxatdan o‘tish$'), register_start),
            ],
            states={
                REGISTER_ROLE: [CallbackQueryHandler(register_role, pattern='^role:')],
                REGISTER_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, register_phone)],
                REGISTER_TRUCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_truck)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        load_conv = ConversationHandler(
            entry_points=[
                CommandHandler('newload', newload_start),
                MessageHandler(filters.Regex('^Yuk joylash$'), newload_start),
            ],
            states={
                LOAD_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_from)],
                LOAD_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_to)],
                LOAD_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_volume)],
                LOAD_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_weight)],
                LOAD_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_type)],
                LOAD_VEHICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_vehicle)],
                LOAD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_price)],
                LOAD_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, load_phone)],
                LOAD_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_note)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        app.add_handler(register_conv)
        app.add_handler(load_conv)
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('loads', loads_command))
        app.add_handler(CommandHandler('myloads', myloads_command))
        app.add_handler(CommandHandler('nearloads', nearloads_command))
        app.add_handler(CallbackQueryHandler(cancel_load_callback, pattern='^cancel_load:'))
        app.add_handler(CallbackQueryHandler(accept_callback, pattern='^accept:'))
        app.add_handler(MessageHandler(filters.LOCATION, location_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

        self.stdout.write(self.style.SUCCESS('Telegram bot ishga tushdi'))
        app.run_polling()
