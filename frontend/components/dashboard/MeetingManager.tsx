// This component has been replaced by MeetingCard and MeetingDetail
// Functionality moved to individual card components for better modularity

import React from 'react';

const MeetingManager: React.FC = () => {
    return (
        <div className="p-6">
            <h2 className="text-2xl font-bold mb-4">Meeting Manager</h2>
            <p>This component is deprecated. Use MeetingCard and MeetingDetail instead.</p>
        </div>
    );
};

export default MeetingManager;
