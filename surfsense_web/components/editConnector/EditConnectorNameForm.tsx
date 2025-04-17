import React from 'react';
import { Control } from 'react-hook-form';
import { FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";

// Assuming EditConnectorFormValues is defined elsewhere or passed as generic
interface EditConnectorNameFormProps {
    control: Control<any>; // Use Control<EditConnectorFormValues> if type is available
}

export function EditConnectorNameForm({ control }: EditConnectorNameFormProps) {
    return (
        <FormField
            control={control}
            name="name"
            render={({ field }) => (
                <FormItem>
                    <FormLabel>Connector Name</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                </FormItem>
            )}
        />
    );
} 
