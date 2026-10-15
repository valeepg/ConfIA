import {
  collection,
  doc,
  getDocs,
  serverTimestamp,
  setDoc,
  writeBatch,
} from 'firebase/firestore';

import { INITIAL_CONSUMABLES, INITIAL_LEADS, INITIAL_MAINTENANCE, INITIAL_TRAINING } from '@/data/mockData';
import type { InstalledBaseRecord, Lead, ProposalDocument, ProposalType } from '@/types';
import { firebaseDb } from './firebase';

const PROSPECTS_COLLECTION = 'prospects';
const PROPOSALS_COLLECTION = 'proposals';
const INSTALLED_BASE_COLLECTION = 'installed_base';

function withoutUndefined<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map(withoutUndefined) as T;
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, entry]) => entry !== undefined)
        .map(([key, entry]) => [key, withoutUndefined(entry)]),
    ) as T;
  }

  return value;
}

function requireDatabase() {
  if (!firebaseDb) {
    throw new Error('Firebase no está habilitado o faltan variables de entorno.');
  }

  return firebaseDb;
}

export async function getProspects(): Promise<Lead[]> {
  const snapshot = await getDocs(collection(requireDatabase(), PROSPECTS_COLLECTION));

  return snapshot.docs.map((prospect) => ({
    ...prospect.data(),
    id: prospect.id,
  })) as Lead[];
}

export async function saveProspect(lead: Lead): Promise<void> {
  const database = requireDatabase();
  await setDoc(
    doc(database, PROSPECTS_COLLECTION, lead.id),
    withoutUndefined({
      ...lead,
      updatedAt: serverTimestamp(),
    }),
    { merge: true },
  );
}

export async function seedProspectsFromMocks(): Promise<void> {
  const database = requireDatabase();
  const batch = writeBatch(database);

  INITIAL_LEADS.forEach((lead) => {
    batch.set(
      doc(database, PROSPECTS_COLLECTION, lead.id),
      withoutUndefined({
        ...lead,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      }),
      { merge: true },
    );
  });

  await batch.commit();
}

export async function saveProposal(
  proposal: Omit<ProposalDocument, 'id'> & { id: string },
): Promise<void> {
  const database = requireDatabase();

  await setDoc(
    doc(database, PROPOSALS_COLLECTION, proposal.id),
    withoutUndefined({
      ...proposal,
      updatedAt: serverTimestamp(),
      createdAt: serverTimestamp(),
    }),
    { merge: true },
  );
}

export async function seedInstalledBaseFromMocks(): Promise<void> {
  const database = requireDatabase();
  const batch = writeBatch(database);

  const records: InstalledBaseRecord[] = INITIAL_CONSUMABLES.map((item) => {
    const maintenance = INITIAL_MAINTENANCE.find((entry) => entry.clinicName === item.clinicName);

    return {
      id: item.id,
      clinicName: item.clinicName,
      equipmentModel: 'Generador O3 Médico Sistémico OzoLife Digital Clase IIb',
      installationDate: '2026-01-15',
      consumableStatus: item.status,
      lastOrderText: item.lastOrderText,
      maintenanceTask: maintenance?.task,
      maintenanceDueInText: maintenance?.dueInText,
      maintenanceUrgency: maintenance?.urgency,
      trainingProgress: INITIAL_TRAINING,
    };
  });

  records.forEach((record) => {
    batch.set(
      doc(database, INSTALLED_BASE_COLLECTION, record.id),
      withoutUndefined({
        ...record,
        updatedAt: serverTimestamp(),
      }),
      { merge: true },
    );
  });

  await batch.commit();
}

export function proposalId(prospectId: string, type: ProposalType) {
  return `${prospectId}-${type}`;
}
