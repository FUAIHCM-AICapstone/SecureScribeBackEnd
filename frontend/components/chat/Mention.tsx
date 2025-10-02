import type { Mention as MentionType } from '../../types/chat.type';

interface MentionProps {
    mention: MentionType;
    children: React.ReactNode;
}

export default function Mention({ mention, children }: MentionProps) {
    const handleClick = () => {
        // Handle mention click - could navigate to entity or show details
        console.log('Mention clicked:', mention);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
        }
    };

    return (
        <span
            className={`mention mention-${mention.entity_type} cursor-pointer`}
            data-entity-id={mention.entity_id}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            tabIndex={0}
            role="button"
            title={`${mention.entity_type}: ${mention.entity_id}`}
        >
            {children}
        </span>
    );
}
