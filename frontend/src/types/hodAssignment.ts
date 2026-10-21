export interface HodAssignment {
  id: number;
  hod_user_id: number;
  hod_name: string;
  hod_email: string;
  department_id: number;
  department_name: string;
}

export interface HodAssignmentCreate {
  hod_user_id: number;
  department_id: number;
}
