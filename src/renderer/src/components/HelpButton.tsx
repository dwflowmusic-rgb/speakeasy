import { useState } from "react"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@renderer/components/ui/dialog"
import { Button } from "@renderer/components/ui/button"

interface HelpButtonProps {
    module: "gemini" | "openai" | "groq"
}

const helpContent = {
    gemini: {
        title: "Como obter sua API Key do Google Gemini",
        steps: [
            "1. Acesse o Google AI Studio: https://aistudio.google.com/",
            "2. Faça login com sua conta Google",
            "3. Clique em 'Get API Key' no menu lateral",
            "4. Crie uma nova chave ou copie uma existente",
            "5. Cole a chave no campo acima",
        ],
    },
    openai: {
        title: "Como obter sua API Key da OpenAI",
        steps: [
            "1. Acesse: https://platform.openai.com/api-keys",
            "2. Faça login com sua conta OpenAI",
            "3. Clique em 'Create new secret key'",
            "4. Dê um nome à chave e copie-a",
            "5. Cole a chave no campo acima",
        ],
    },
    groq: {
        title: "Como obter sua API Key do Groq",
        steps: [
            "1. Acesse: https://console.groq.com/keys",
            "2. Crie uma conta ou faça login",
            "3. Clique em 'Create API Key'",
            "4. Copie a chave gerada",
            "5. Cole a chave no campo acima",
        ],
    },
}

export function HelpButton({ module }: HelpButtonProps) {
    const [open, setOpen] = useState(false)
    const content = helpContent[module]

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 rounded-full p-0 text-muted-foreground hover:text-foreground"
                >
                    ?
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{content.title}</DialogTitle>
                </DialogHeader>
                <div className="space-y-2 text-sm text-muted-foreground">
                    {content.steps.map((step, index) => (
                        <p key={index}>{step}</p>
                    ))}
                </div>
            </DialogContent>
        </Dialog>
    )
}
