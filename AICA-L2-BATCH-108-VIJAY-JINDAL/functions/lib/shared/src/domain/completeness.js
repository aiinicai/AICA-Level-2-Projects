/** Drives the "complete your profile" progress bar and the incomplete-profiles dashboard. */
export function profileCompleteness(core, sub, dra) {
    const checks = [
        ['fullName', Boolean(core.fullName)],
        ['location', Boolean(core.location?.stateCode && core.location.city && core.location.pin)],
        ['district', Boolean(core.location?.district)],
        ['draStatus', Boolean(core.draStatus)],
        ['draDetails', core.draStatus !== 'certified' || Boolean(dra?.certificateNumber && dra.issuer)],
        ['draCertificateUpload', core.draStatus !== 'certified' || Boolean(dra?.certificateFilePath)],
        ['experienceType', core.experienceType != null],
        ['employmentHistory', core.experienceType !== 'experienced' || (sub?.employmentHistory?.length ?? 0) > 0],
        ['education', (sub?.education?.length ?? 0) > 0],
        ['languages', (core.languagesKnown?.length ?? 0) > 0],
        ['preferences', Boolean(sub?.preferences?.preferredRoles?.length)],
        ['photo', Boolean(core.profilePhotoPath)],
    ];
    const missing = checks.filter(([, ok]) => !ok).map(([k]) => k);
    const percent = Math.round(((checks.length - missing.length) / checks.length) * 100);
    const level = percent === 100 ? 'complete' : sub || core.experienceType != null ? 'partial' : 'registration_only';
    return { level, percent, missing };
}
//# sourceMappingURL=completeness.js.map