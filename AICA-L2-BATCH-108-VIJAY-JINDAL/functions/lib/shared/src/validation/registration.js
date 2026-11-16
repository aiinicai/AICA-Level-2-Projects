import { isValidStateCode, pinMatchesState } from '../geo/states.js';
import { cleanText, isValidPersonName, isValidPin } from './basic.js';
export const ROLES = [
    'field_collection',
    'telecalling',
    'backend',
    'team_leader',
    'supervisor',
    'manager',
    'regional_manager',
    'zonal_head',
    'state_head',
    'national_head',
    'other',
];
export const DRA_STATUSES = ['certified', 'training_in_progress', 'result_awaited', 'not_certified'];
export function validateRegistration(input) {
    const errors = {};
    const fullName = cleanText(input.fullName, 80);
    const city = cleanText(input.city, 80);
    if (!isValidPersonName(fullName))
        errors.fullName = 'name_invalid';
    if (!isValidStateCode(input.stateCode))
        errors.stateCode = 'state_required';
    if (city.length < 2)
        errors.city = 'city_required';
    if (!isValidPin(input.pin))
        errors.pin = 'pin_invalid';
    if (!DRA_STATUSES.includes(input.draStatus))
        errors.draStatus = 'dra_status_required';
    if (!ROLES.includes(input.preferredRole))
        errors.preferredRole = 'role_required';
    if (!['en', 'hi', 'pa'].includes(input.preferredLanguage))
        errors.preferredLanguage = 'language_invalid';
    if (input.ageAttestation18Plus !== true)
        errors.ageAttestation18Plus = 'age_18_required';
    if (input.consents?.privacyNotice !== true)
        errors.privacyNotice = 'privacy_required';
    if (input.consents?.terms !== true)
        errors.terms = 'terms_required';
    if (input.consents?.recruitmentContact !== true)
        errors.recruitmentContact = 'contact_consent_required';
    if (!input.noticeVersion)
        errors.noticeVersion = 'notice_version_missing';
    const referralCode = input.referralCode ? input.referralCode.trim().toUpperCase() : undefined;
    if (referralCode && !/^R[0-9A-HJKMNP-TV-Z]{6}$/.test(referralCode))
        errors.referralCode = 'referral_invalid';
    if (Object.keys(errors).length)
        return { ok: false, errors };
    return {
        ok: true,
        value: {
            ...input, fullName, city, referralCode,
            campaign: input.campaign ? cleanText(input.campaign, 40).replace(/[^a-zA-Z0-9_-]/g, '') : undefined,
            pinMismatch: !pinMatchesState(input.pin, input.stateCode),
        },
    };
}
//# sourceMappingURL=registration.js.map