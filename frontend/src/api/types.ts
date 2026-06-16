// Convenience aliases over the generated OpenAPI types so application code
// never reaches into components['schemas'] directly.

import type { components } from './types.gen';

export type UserRead = components['schemas']['UserRead'];
export type UserUpdate = components['schemas']['UserUpdate'];
export type LocationRead = components['schemas']['LocationRead'];
export type LocationCreate = components['schemas']['LocationCreate'];
export type LocationUpdate = components['schemas']['LocationUpdate'];
export type PlantRead = components['schemas']['PlantRead'];
export type PlantListItem = components['schemas']['PlantListItem'];
export type PlantDetail = components['schemas']['PlantDetail'];
export type PlantCreate = components['schemas']['PlantCreate'];
export type PlantUpdate = components['schemas']['PlantUpdate'];
export type PhotoRead = components['schemas']['PhotoRead'];
export type CareLogRead = components['schemas']['CareLogRead'];
export type CareLogCreate = components['schemas']['CareLogCreate'];
export type ReminderRead = components['schemas']['ReminderRead'];
export type ReminderCreate = components['schemas']['ReminderCreate'];
export type ReminderUpdate = components['schemas']['ReminderUpdate'];
export type ReminderStatus = components['schemas']['ReminderStatus'];
export type DashboardSummary = components['schemas']['DashboardSummary'];
export type SpeciesSearchResult = components['schemas']['SpeciesSearchResult'];
