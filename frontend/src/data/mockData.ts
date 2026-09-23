import type { Campaign, DashboardData, DataLimits, Pilot, SimulationData } from '../types/api'

export const mockDashboard: DashboardData = {
  baselineArpu: 150_641_084, campaignNetGain: 3_630_000, budgetUsed: 71_840, budgetLimit: 100_000,
  contactsUsed: 8_940, contactsLimit: 15_000, pilotsUsed: 14, pilotsLimit: 20, finalCampaigns: 5, finalCampaignLimit: 10, status: 'PASS',
  channelBudget: [{ name: 'Пуш', value: 8_640 }, { name: 'SMS', value: 31_200 }, { name: 'Цифровая реклама', value: 32_000 }],
  campaignNet: [{ name: 'Семья', value: 980 }, { name: 'Выходной', value: 760 }, { name: 'Мега', value: 710 }, { name: 'Комфорт', value: 640 }, { name: 'Больше минут', value: 540 }],
  audienceCoverage: [{ name: 'В охвате', value: 8_940 }, { name: 'Осталось', value: 6_060 }],
}

export const mockCampaigns: Campaign[] = [
  { id: 'C-01', name: 'Семейное предложение', currentTariff: 'Всё включено', arpuSegment: 'Высокий ARPU', targetTariff: 'Премиум Семья', channel: 'SMS', audienceSize: 1_240, communicationCost: 24_800, expectedGrossLift: 1_260_000, expectedNetGain: 980_000, confidence: 'High', status: 'Ready', rationale: 'Подтверждающий пилот показывает устойчивую положительную нижнюю границу эффекта.' },
  { id: 'C-02', name: 'Интернет на выходные', currentTariff: 'Старт', arpuSegment: 'Средний ARPU', targetTariff: 'Выходной 5 990', channel: 'Push', audienceSize: 3_180, communicationCost: 0, expectedGrossLift: 760_000, expectedNetGain: 760_000, confidence: 'High', status: 'Ready', rationale: 'Пользователям с высоким потреблением трафика релевантен расширенный пакет на бесплатном канале.' },
  { id: 'C-03', name: 'Больше мобильного интернета', currentTariff: 'Интернет+', arpuSegment: 'Средний ARPU', targetTariff: 'Мега 7 999', channel: 'Digital ads', audienceSize: 860, communicationCost: 17_200, expectedGrossLift: 727_000, expectedNetGain: 710_000, confidence: 'Medium', status: 'Ready', rationale: 'Цифровая реклама показала лучший результат для визуального предложения с большим пакетом данных.' },
  { id: 'C-04', name: 'Переход на комфортный тариф', currentTariff: 'Комфорт Лайт', arpuSegment: 'Низкий ARPU', targetTariff: 'Комфорт', channel: 'Digital ads', audienceSize: 1_440, communicationCost: 14_800, expectedGrossLift: 655_000, expectedNetGain: 640_000, confidence: 'Medium', status: 'Ready', rationale: 'Контрольный пилот дал положительный взвешенный результат после стоимости канала.' },
  { id: 'C-05', name: 'Больше минут', currentTariff: 'Старт', arpuSegment: 'Низкий ARPU', targetTariff: 'Больше минут 4 990', channel: 'SMS', audienceSize: 2_220, communicationCost: 6_400, expectedGrossLift: 546_000, expectedNetGain: 540_000, confidence: 'Testing', status: 'Testing', rationale: 'Первый эффект положительный; идёт последний подтверждающий пилот.' },
]

export const mockPilots: Pilot[] = [
  { id: 'P-01', phase: 'Initial', title: 'Семейное предложение', audience: 120, result: '+18,4% чистый эффект', confidence: 94, status: 'Completed' },
  { id: 'P-02', phase: 'Initial', title: 'Интернет на выходные', audience: 120, result: '+13,1% чистый эффект', confidence: 91, status: 'Completed' },
  { id: 'P-09', phase: 'Initial', title: 'Больше мобильного интернета', audience: 120, result: '+9,6% чистый эффект', confidence: 78, status: 'Completed' },
  { id: 'P-11', phase: 'Confirmation', title: 'Семейное предложение', audience: 200, result: 'Подтверждено', confidence: 96, status: 'Completed' },
  { id: 'P-14', phase: 'Confirmation', title: 'Больше минут', audience: 200, result: 'Собираем данные', confidence: 62, status: 'Running' },
]

export const mockSimulation: SimulationData = {
  profitableRuns: 100, totalRuns: 100, medianNet: 3_630_000, minimumNet: 2_020_000, maximumNet: 4_110_000, controlSeedNet: 2_580_000,
  distribution: [{ bin: '2,0 млн', count: 4 }, { bin: '2,5 млн', count: 18 }, { bin: '3,0 млн', count: 31 }, { bin: '3,5 млн', count: 29 }, { bin: '4,0 млн', count: 18 }],
  comparison: [{ name: 'Только пуш', value: 2.58 }, { name: 'Оптимальный канал', value: 3.63 }], source: 'demo',
}

export const mockLimits: DataLimits = {
  subscribers: 23_441, baselineArpu: 150_641_084, budget: 100_000, contacts: 15_000, pilots: 20, pilotSize: 200, finalCampaigns: 10, campaignSize: 5_000,
  channels: [{ name: 'Push', cost: 0, multiplier: '1.00×' }, { name: 'SMS', cost: 20, multiplier: '1.16×' }, { name: 'Digital ads', cost: 20, multiplier: '1.22×' }, { name: 'Call', cost: 180, multiplier: '1.38×' }],
}
