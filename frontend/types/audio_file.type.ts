// Audio File Management Types
// Based on backend schemas from app/schemas/audio_file.py

import type { ApiResponse } from './common.type';

export interface AudioFileBase {
    meeting_id: string;
    file_url?: string;
    seq_order?: number;
    duration_seconds?: number;
}

export interface AudioFileCreate extends AudioFileBase {
    uploaded_by: string;
}

export interface AudioFileUpdate {
    seq_order?: number;
    duration_seconds?: number;
}

export interface AudioFileResponse {
    id: string;
    meeting_id: string;
    uploaded_by: string;
    file_url?: string;
    seq_order?: number;
    duration_seconds?: number;
    is_concatenated: boolean;
    created_at: string;
    updated_at?: string;
}

export interface BulkAudioFileCreate {
    audio_files: AudioFileCreate[];
}

export interface BulkAudioFileUpdateItem {
    id: string;
    updates: AudioFileUpdate;
}

export interface BulkAudioFileUpdate {
    audio_files: BulkAudioFileUpdateItem[];
}

export interface BulkAudioFileDelete {
    audio_file_ids: string[];
}

export interface BulkAudioFileResponse {
    success: boolean;
    message: string;
    data: any[];
    total_processed: number;
    total_success: number;
    total_failed: number;
}

export type AudioFileApiResponse = ApiResponse<AudioFileResponse>;
export type BulkAudioFileApiResponse = ApiResponse<BulkAudioFileResponse>;
