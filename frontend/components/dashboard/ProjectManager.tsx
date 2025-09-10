// This component has been replaced by ProjectCard and ProjectDetail
// Functionality moved to individual card components for better modularity

import React from 'react';

const ProjectManager: React.FC = () => {
    return (
        <div className="p-6">
            <h2 className="text-2xl font-bold mb-4">Project Manager</h2>
            <p>This component is deprecated. Use ProjectCard and ProjectDetail instead.</p>
        </div>
    );
};

export default ProjectManager;
